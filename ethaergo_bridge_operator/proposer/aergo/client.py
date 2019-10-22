import argparse
from getpass import getpass
import time
import threading

import aergo.herapy as herapy

from ethaergo_bridge_operator.op_utils import (
    query_aergo_tempo,
    query_aergo_validators,
    query_unfreeze_fee,
    load_config_data,
)
from ethaergo_bridge_operator.proposer.exceptions import (
    ValidatorMajorityError,
)
from web3 import (
    Web3,
)
from web3.middleware import (
    geth_poa_middleware,
)
from ethaergo_bridge_operator.proposer.aergo.validator_connect import (
    AergoValConnect,
)
from ethaergo_bridge_operator.proposer.aergo.transact import (
    AergoTx,
)


class AergoProposerClient(threading.Thread):
    """The bridge proposer periodically (every t_anchor) broadcasts
    the finalized trie state root (after lib) of the bridge contract
    on both sides of the bridge after validation by the Validator servers.
    It first checks the last merged height and waits until
    now > lib + t_anchor is reached, then merges the current finalised
    block (lib). Start again after waiting t_anchor.

    Note on config_data:
        - config_data is used to store current validators and their ip when the
          proposer starts. (change validators after the proposer has started)
        - After starting, when users change the config.json, the proposer will
          attempt to gather signatures to reflect the changes.
        - t_anchor value is always taken from the bridge contract
        - validators are taken from the config_data because ip information is
          not stored on chain
        - when a validator set update succeeds, self.config_data is updated
        - if another proposer updates to a new set of validators and the
          proposer doesnt know about it, proposer must be restarted with the
          new current validator set to create new connections to them.

    """

    def __init__(
        self,
        config_file_path: str,
        aergo_net: str,
        eth_net: str,
        eth_block_time: int,
        privkey_name: str = None,
        privkey_pwd: str = None,
        tab: str = "",
        auto_update: bool = False,
        aergo_gas_price: int = None
    ) -> None:
        threading.Thread.__init__(self)
        if aergo_gas_price is None:
            aergo_gas_price = 0
        self.aergo_gas_price = aergo_gas_price
        self.config_file_path = config_file_path
        config_data = load_config_data(self.config_file_path)
        self.eth_block_time = eth_block_time
        self.tab = tab
        self.eth_net = eth_net
        self.aergo_net = aergo_net
        self.auto_update = auto_update
        print("------ Connect Aergo and Ethereum -----------")
        self.hera = herapy.Aergo()
        self.hera.connect(config_data['networks'][aergo_net]['ip'])

        ip = config_data['networks'][eth_net]['ip']
        self.web3 = Web3(Web3.HTTPProvider(ip))
        eth_poa = config_data['networks'][eth_net]['isPOA']
        if eth_poa:
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        assert self.web3.isConnected()

        self.eth_bridge = (config_data['networks'][eth_net]['bridges']
                           [aergo_net]['addr'])
        self.aergo_bridge = (config_data['networks'][aergo_net]['bridges']
                             [eth_net]['addr'])

        # get the current t_anchor and t_final for both sides of bridge
        self.t_anchor, self.t_final = query_aergo_tempo(
            self.hera, self.aergo_bridge
        )
        print("{}              <- {} (t_final={}) : t_anchor={}"
              .format(aergo_net, eth_net, self.t_final, self.t_anchor))

        print("------ Set Sender Account -----------")
        if privkey_name is None:
            privkey_name = 'proposer'
        if privkey_pwd is None:
            privkey_pwd = getpass("Decrypt exported private key '{}'\n"
                                  "Password: ".format(privkey_name))
        sender_priv_key = config_data['wallet'][privkey_name]['priv_key']
        self.aergo_tx = AergoTx(
            self.hera, sender_priv_key, privkey_pwd, self.aergo_bridge,
            aergo_gas_price, self.t_anchor, eth_block_time, tab
        )

        print("------ Connect to Validators -----------")
        self.val_connect = AergoValConnect(
            config_data, self.hera, self.aergo_bridge, tab)

    def wait_next_anchor(
        self,
        merged_height: int,
    ) -> int:
        """ Wait until t_anchor has passed after merged height.
        Return the next finalized block after t_anchor to be the next anchor
        """
        best_height = self.web3.eth.blockNumber
        lib = best_height - self.t_final
        # wait for merged_height + t_anchor > lib
        wait = (merged_height + self.t_anchor) - lib + 1
        while wait > 0:
            print("{}{} waiting new anchor time : {}s ..."
                  .format(self.tab, u'\u23F0', wait * self.eth_block_time))
            self.monitor_settings_and_sleep(wait * self.eth_block_time)
            # Wait lib > last merged block height + t_anchor
            best_height = self.web3.eth.blockNumber
            lib = best_height - self.t_final
            wait = (merged_height + self.t_anchor) - lib + 1
        return lib

    def run(
        self,
    ) -> None:
        """ Gathers signatures from validators, verifies them, and if 2/3 majority
        is acquired, set the new anchored root in aergo_bridge.
        """
        while True:  # anchor a new root
            # Get last merge information
            status = self.hera.query_sc_state(self.aergo_bridge,
                                              ["_sv__anchorHeight",
                                               "_sv__anchorRoot",
                                               "_sv__nonce",
                                               "_sv__tAnchor",
                                               "_sv__tFinal"
                                               ])
            height_from, root_from, nonce_to, t_anchor, t_final = \
                [proof.value for proof in status.var_proofs]
            merged_height_from = int(height_from)
            nonce_to = int(nonce_to)
            self.t_anchor = int(t_anchor)
            self.t_final = int(t_final)

            print("\n{0}| Last anchor from Ethereum:\n"
                  "{0}| --------------------------\n"
                  "{0}| height: {1}\n"
                  "{0}| contract trie root: 0x{2}...\n"
                  "{0}| current update nonce: {3}\n"
                  .format(self.tab, merged_height_from,
                          root_from.decode('utf-8')[1:20], nonce_to))

            # Wait for the next anchor time
            next_anchor_height = self.wait_next_anchor(merged_height_from)
            # Get root of next anchor to broadcast
            state = self.web3.eth.getProof(
                self.eth_bridge, [], next_anchor_height)
            root = state.storageHash.hex()[2:]
            if len(root) == 0:
                print("{}waiting deployment finalization..."
                      .format(self.tab))
                time.sleep(5)
                continue

            print("{}anchoring new Ethereum root :'0x{}...'"
                  .format(self.tab, root[:17]))
            print("{}{} Gathering signatures from validators ..."
                  .format(self.tab, u'\U0001f58b'))

            nonce_to = int(self.hera.query_sc_state(
                self.aergo_bridge, ["_sv__nonce"]
            ).var_proofs[0].value)

            try:
                sigs, validator_indexes = \
                    self.val_connect.get_anchor_signatures(
                        root, next_anchor_height, nonce_to)
            except ValidatorMajorityError:
                print("{0}Failed to gather 2/3 validators signatures,\n"
                      "{0}{1} waiting for next anchor..."
                      .format(self.tab, u'\u23F0'))
                self.monitor_settings_and_sleep(
                    self.t_anchor * self.eth_block_time)
                continue

            # don't broadcast if somebody else already did
            last_merge = self.hera.query_sc_state(self.aergo_bridge,
                                                  ["_sv__anchorHeight"])
            merged_height = int(last_merge.var_proofs[0].value)
            if merged_height + self.t_anchor >= next_anchor_height:
                print("{}Not yet anchor time "
                      "or another proposer already anchored".format(self.tab))
                wait = merged_height + self.t_anchor - next_anchor_height
                self.monitor_settings_and_sleep(wait * self.eth_block_time)
                continue

            # Broadcast finalised merge block
            self.aergo_tx.new_anchor(
                root, next_anchor_height, validator_indexes, sigs)
            self.monitor_settings_and_sleep(
                self.t_anchor * self.eth_block_time)

    def monitor_settings_and_sleep(self, sleeping_time):
        """While sleeping, periodicaly check changes to the config
        file and update settings if necessary. If another
        proposer updated settings it doesnt matter, validators will
        just not give signatures.

        """
        if self.auto_update:
            start = time.time()
            self.monitor_settings()
            while time.time()-start < sleeping_time-10:
                # check the config file every 10 seconds
                time.sleep(10)
                self.monitor_settings()
            remaining = sleeping_time - (time.time() - start)
            if remaining > 0:
                time.sleep(remaining)
        else:
            time.sleep(sleeping_time)

    def monitor_settings(self):
        """Check if a modification of bridge settings is requested by seeing
        if the config file has been changed and try to update the bridge
        contract (gather 2/3 validators signatures).

        """
        config_data = load_config_data(self.config_file_path)
        validators = query_aergo_validators(self.hera, self.aergo_bridge)
        t_anchor, t_final = query_aergo_tempo(self.hera, self.aergo_bridge)
        unfreeze_fee = query_unfreeze_fee(self.hera, self.aergo_bridge)
        config_validators = [val['addr']
                             for val in config_data['validators']]
        if validators != config_validators:
            print('{}Validator set update requested'.format(self.tab))
            if self.update_validators(config_validators):
                self.val_connect.use_new_validators(config_data)
        config_t_anchor = (config_data['networks'][self.aergo_net]['bridges']
                           [self.eth_net]['t_anchor'])
        if t_anchor != config_t_anchor:
            print('{}Anchoring periode update requested'.format(self.tab))
            self.update_t_anchor(config_t_anchor)
        config_t_final = (config_data['networks'][self.aergo_net]['bridges']
                          [self.eth_net]['t_final'])
        if t_final != config_t_final:
            print('{}Finality update requested'.format(self.tab))
            self.update_t_final(config_t_final)
        config_unfreeze_fee = (config_data['networks'][self.aergo_net]
                               ['bridges'][self.eth_net]['unfreeze_fee'])
        if unfreeze_fee != config_unfreeze_fee:
            print('{}Unfreeze fee update requested'.format(self.tab))
            self.update_unfreeze_fee(config_unfreeze_fee)

    def update_validators(self, new_validators):
        """Try to update the validator set with the one in the config file."""
        try:
            sigs, validator_indexes = \
                self.val_connect.get_new_validators_signatures(new_validators)
        except ValidatorMajorityError:
            print("{0}Failed to gather 2/3 validators signatures"
                  .format(self.tab))
            return False
        # broadcast transaction
        return self.aergo_tx.set_validators(
            new_validators, validator_indexes, sigs)

    def update_t_anchor(self, t_anchor):
        """Try to update the anchoring periode registered in the bridge
        contract.

        """
        try:
            sigs, validator_indexes = \
                self.val_connect.get_tempo_signatures(
                    t_anchor, "GetEthTAnchorSignature", "A")
        except ValidatorMajorityError:
            print("{0}Failed to gather 2/3 validators signatures"
                  .format(self.tab))
            return
        # broadcast transaction
        self.aergo_tx.set_single_param(
            t_anchor, validator_indexes, sigs, "tAnchorUpdate", "\u231B")

    def update_t_final(self, t_final):
        """Try to update the anchoring periode registered in the bridge
        contract.

        """
        try:
            sigs, validator_indexes = \
                self.val_connect.get_tempo_signatures(
                    t_final, "GetEthTFinalSignature", "F")
        except ValidatorMajorityError:
            print("{0}Failed to gather 2/3 validators signatures"
                  .format(self.tab))
            return
        # broadcast transaction
        self.aergo_tx.set_single_param(
            t_final, validator_indexes, sigs, "tFinalUpdate", "\u231B")

    def update_unfreeze_fee(self, fee):
        """Try to update the anchoring periode registered in the bridge
        contract.

        """
        try:
            sigs, validator_indexes = \
                self.val_connect.get_unfreeze_fee_signatures(fee)
        except ValidatorMajorityError:
            print("{0}Failed to gather 2/3 validators signatures"
                  .format(self.tab))
            return
        # broadcast transaction
        self.aergo_tx.set_single_param(
            {'_bignum': str(fee)}, validator_indexes, sigs,
            "unfreezeFeeUpdate", "\U0001f4a7"
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Start a proposer on Ethereum and Aergo.')
    # Add arguments
    parser.add_argument(
        '-c', '--config_file_path', type=str, help='Path to config.json',
        required=True)
    parser.add_argument(
        '-a', '--aergo', type=str, help='Name of Aergo network in config file',
        required=True)
    parser.add_argument(
        '-e', '--eth', help='Name of Ethereum network in config file',
        type=str, required=True)
    parser.add_argument(
        '--eth_block_time', type=int, help='Average Ethereum block time',
        required=True)
    parser.add_argument(
        '--privkey_name', type=str, help='Name of account in config file '
        'to sign anchors', required=False)
    parser.add_argument(
        '--auto_update', dest='auto_update', action='store_true',
        help='Update bridge contract when settings change in config file')
    parser.add_argument(
        '--aergo_gas_price', type=int,
        help='Gas price to use in transactions', required=False)
    parser.set_defaults(auto_update=False)
    parser.set_defaults(aergo_gas_price=None)
    args = parser.parse_args()

    proposer = AergoProposerClient(
        args.config_file_path, args.aergo, args.eth, args.eth_block_time,
        privkey_name=args.privkey_name, auto_update=args.auto_update,
        aergo_gas_price=args.aergo_gas_price
    )
    proposer.run()
