import argparse
from getpass import getpass
import threading
import time


import aergo.herapy as herapy
from web3 import (
    Web3,
)
from web3.middleware import (
    geth_poa_middleware,
)

from ethaergo_bridge_operator.op_utils import (
    load_config_data,
)
from ethaergo_bridge_operator.proposer.exceptions import (
    ValidatorMajorityError,
)
from ethaergo_bridge_operator.proposer.eth.validator_connect import (
    EthValConnect,
)
from ethaergo_bridge_operator.proposer.eth.transact import (
    EthTx,
)


class EthProposerClient(threading.Thread):
    """The ethereum bridge proposer periodically (every t_anchor) broadcasts
    the finalized Aergo trie state root (after lib) of the bridge contract
    onto the ethereum bridge contract after validation by the Validators.
    It first checks the last merged height and waits until
    now > lib + t_anchor is reached, then merges the current finalised
    block (lib). Start again after waiting t_anchor.
    EthProposerClient anchors an Aergo state root onto Ethereum.

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
        privkey_name: str = None,
        privkey_pwd: str = None,
        tab: str = "",
        auto_update: bool = False,
        root_path: str = './',
        eth_gas_price: int = None
    ) -> None:
        threading.Thread.__init__(self)
        if eth_gas_price is None:
            eth_gas_price = 10
        self.config_file_path = config_file_path
        config_data = load_config_data(config_file_path)
        self.tab = tab
        self.eth_net = eth_net
        self.aergo_net = aergo_net
        self.auto_update = auto_update
        print("------ Connect Aergo and Ethereum -----------")
        self.hera = herapy.Aergo()
        self.hera.connect(config_data['networks'][aergo_net]['ip'])

        # Web3 instance for reading blockchains state, shared with
        # EthValConnect.
        ip = config_data['networks'][eth_net]['ip']
        self.web3 = Web3(Web3.HTTPProvider(ip))
        eth_poa = config_data['networks'][eth_net]['isPOA']
        if eth_poa:
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        assert self.web3.isConnected()

        bridge_abi_path = (config_data['networks'][eth_net]['bridges']
                           [aergo_net]['bridge_abi'])
        with open(bridge_abi_path, "r") as f:
            self.eth_abi = f.read()
        self.eth_bridge_address = (config_data['networks'][eth_net]
                                   ['bridges'][aergo_net]['addr'])
        self.eth_bridge = self.web3.eth.contract(
            address=self.eth_bridge_address,
            abi=self.eth_abi
        )
        self.aergo_bridge = (config_data['networks'][aergo_net]['bridges']
                             [eth_net]['addr'])

        # get the current t_anchor and t_final for anchoring on etherem
        self.t_anchor = self.eth_bridge.functions._tAnchor().call()
        self.t_final = self.eth_bridge.functions._tFinal().call()
        print("{} (t_final={}) -> {} : t_anchor={}"
              .format(aergo_net, self.t_final, eth_net, self.t_anchor))

        print("------ Set Sender Account -----------")
        if privkey_name is None:
            privkey_name = 'proposer'
        keystore = config_data["wallet-eth"][privkey_name]['keystore']
        with open(root_path + keystore, "r") as f:
            encrypted_key = f.read()
        if privkey_pwd is None:
            privkey_pwd = getpass("Decrypt Ethereum keystore '{}'\n"
                                  "Password: ".format(privkey_name))
        self.eth_tx = EthTx(
            self.web3, encrypted_key, privkey_pwd, self.eth_bridge_address,
            self.eth_abi, eth_gas_price, self.t_anchor, tab)

        print("------ Connect to Validators -----------")
        self.val_connect = EthValConnect(
            config_data, self.web3, self.eth_bridge_address,
            self.eth_abi, tab
        )

    def wait_next_anchor(
        self,
        merged_height: int,
    ) -> int:
        """ Wait until t_anchor has passed after merged height.
        Return the next finalized block after t_anchor to be the next anchor
        """
        lib = self.hera.get_status().consensus_info.status['LibNo']
        wait = (merged_height + self.t_anchor) - lib + 1
        while wait > 0:
            print("{}{} waiting new anchor time : {}s ..."
                  .format(self.tab, u'\u23F0', wait))
            self.monitor_settings_and_sleep(wait)
            # Wait lib > last merged block height + t_anchor
            lib = self.hera.get_status().consensus_info.status['LibNo']
            wait = (merged_height + self.t_anchor) - lib + 1
        return lib

    def run(
        self,
    ) -> None:
        """ Gathers signatures from validators, verifies them, and if 2/3 majority
        is acquired, set the new anchored root in eth_bridge.
        """
        print("------ START BRIDGE OPERATOR -----------\n")
        while True:  # anchor a new root
            # Get last merge information
            merged_height_from = self.eth_bridge.functions._anchorHeight().call()
            merged_root_from = self.eth_bridge.functions._anchorRoot().call()
            nonce_to = self.eth_bridge.functions._nonce().call()
            self.t_anchor = self.eth_bridge.functions._tAnchor().call()

            print("\n{0}| Last anchor from Aergo:\n"
                  "{0}| -----------------------\n"
                  "{0}| height: {1}\n"
                  "{0}| contract trie root: 0x{2}...\n"
                  "{0}| current update nonce: {3}\n"
                  .format(self.tab, merged_height_from,
                          merged_root_from.hex()[0:20], nonce_to))

            # Wait for the next anchor time
            next_anchor_height = self.wait_next_anchor(merged_height_from)
            # Get root of next anchor to broadcast
            block = self.hera.get_block(block_height=next_anchor_height)
            contract = self.hera.get_account(
                address=self.aergo_bridge, proof=True,
                root=block.blocks_root_hash
            )
            root = contract.state_proof.state.storageRoot
            if len(root) == 0:
                print("{}waiting deployment finalization..."
                      .format(self.tab))
                time.sleep(5)
                continue

            print("{}anchoring new Aergo root :'0x{}...'"
                  .format(self.tab, root[:8].hex()))
            print("{}{} Gathering signatures from validators ..."
                  .format(self.tab, u'\U0001f58b'))

            try:
                nonce_to = self.eth_bridge.functions._nonce().call()
                sigs, validator_indexes = \
                    self.val_connect.get_anchor_signatures(
                        root, next_anchor_height, nonce_to)
            except ValidatorMajorityError:
                print("{0}Failed to gather 2/3 validators signatures,\n"
                      "{0}{1} waiting for next anchor..."
                      .format(self.tab, u'\u23F0'))
                self.monitor_settings_and_sleep(self.t_anchor)
                continue

            # don't broadcast if somebody else already did
            merged_height = self.eth_bridge.functions._anchorHeight().call()
            if merged_height + self.t_anchor >= next_anchor_height:
                print("{}Not yet anchor time, maybe another proposer"
                      " already anchored".format(self.tab))
                self.monitor_settings_and_sleep(
                    merged_height + self.t_anchor - next_anchor_height)
                continue

            # Broadcast finalised AergoAnchor on Ethereum
            self.eth_tx.new_anchor(
                root, next_anchor_height, validator_indexes, sigs)
            self.monitor_settings_and_sleep(self.t_anchor)

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
        validators = self.eth_bridge.functions.getValidators().call()
        config_validators = [val['eth-addr']
                             for val in config_data['validators']]
        if validators != config_validators:
            print('{}Validator set update requested'.format(self.tab))
            if self.update_validators(config_validators):
                self.val_connect.use_new_validators(config_data)
        t_anchor = self.eth_bridge.functions._tAnchor().call()
        config_t_anchor = (config_data['networks'][self.eth_net]['bridges']
                           [self.aergo_net]['t_anchor'])
        if t_anchor != config_t_anchor:
            print('{}Anchoring periode update requested'.format(self.tab))
            self.update_t_anchor(config_t_anchor)
        t_final = self.eth_bridge.functions._tFinal().call()
        config_t_final = (config_data['networks'][self.eth_net]['bridges']
                          [self.aergo_net]['t_final'])
        if t_final != config_t_final:
            print('{}Finality update requested'.format(self.tab))
            self.update_t_final(config_t_final)

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
        return self.eth_tx.set_validators(new_validators, validator_indexes, sigs)

    def update_t_anchor(self, t_anchor):
        """Try to update the anchoring periode registered in the bridge
        contract.

        """
        try:
            sigs, validator_indexes = self.val_connect.get_tempo_signatures(
                t_anchor, "GetAergoTAnchorSignature", "A")
        except ValidatorMajorityError:
            print("{0}Failed to gather 2/3 validators signatures"
                  .format(self.tab))
            return
        # broadcast transaction
        self.eth_tx.set_t_anchor(t_anchor, validator_indexes, sigs)

    def update_t_final(self, t_final):
        """Try to update the anchoring periode registered in the bridge
        contract.

        """
        try:
            sigs, validator_indexes = self.val_connect.get_tempo_signatures(
                t_final, "GetAergoTFinalSignature", "F")
        except ValidatorMajorityError:
            print("{0}Failed to gather 2/3 validators signatures"
                  .format(self.tab))
            return
        # broadcast transaction
        self.eth_tx.set_t_final(t_final, validator_indexes, sigs)


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
        '-e', '--eth', type=str, required=True,
        help='Name of Ethereum network in config file')
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
        '--eth_gas_price', type=int,
        help='Gas price (gWei) to use in transactions', required=False)
    parser.set_defaults(auto_update=False)
    parser.set_defaults(eth_gas_price=None)
    args = parser.parse_args()

    proposer = EthProposerClient(
        args.config_file_path, args.aergo, args.eth,
        privkey_name=args.privkey_name, auto_update=args.auto_update,
        eth_gas_price=args.eth_gas_price
    )
    proposer.run()
