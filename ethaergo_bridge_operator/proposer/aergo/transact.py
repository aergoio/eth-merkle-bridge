from typing import (
    List,
)

import aergo.herapy as herapy


class AergoTx():
    """ Transact with the aergo bridge contract """

    def __init__(
        self,
        hera: herapy.Aergo,
        encrypted_key: str,
        privkey_pwd: str,
        aergo_bridge: str,
        aergo_gas_price: int,
        t_anchor: int,
        eth_block_time: int,
        tab: str
    ):
        self.aergo_gas_price= aergo_gas_price
        self.t_anchor = t_anchor
        self.eth_block_time = eth_block_time
        self.tab = tab
        self.hera = hera
        self.aergo_bridge = aergo_bridge

        self.hera.import_account(encrypted_key, privkey_pwd)
        print("  > Proposer Address: {}".format(self.hera.account.address))

    def new_anchor(
        self,
        root: str,
        next_anchor_height: int,
        validator_indexes: List[int],
        sigs: List[str],
    ) -> None:
        """Anchor a new root on chain"""
        tx, result = self.hera.call_sc(
            self.aergo_bridge, "newAnchor",
            args=[root, next_anchor_height, validator_indexes, sigs]
        )
        if result.status != herapy.CommitStatus.TX_OK:
            print("{}Anchor on aergo Tx commit failed : {}"
                  .format(self.tab, result))
            return

        result = self.hera.wait_tx_result(tx.tx_hash)
        if result.status != herapy.TxResultStatus.SUCCESS:
            print("{}Anchor failed: already anchored, or invalid "
                  "signature: {}".format(self.tab, result))
        else:
            print("{0}{1} Anchor success,\n{0}{2} wait until next anchor "
                  "time: {3}s..."
                  .format(self.tab, u'\u2693', u'\u23F0',
                          self.t_anchor * self.eth_block_time))

    def set_validators(self, new_validators, validator_indexes, sigs):
        """Update validators on chain"""
        tx, result = self.hera.call_sc(
            self.aergo_bridge, "validatorsUpdate",
            args=[new_validators, validator_indexes, sigs]
        )
        if result.status != herapy.CommitStatus.TX_OK:
            print("{}Set new validators Tx commit failed : {}"
                  .format(self.tab, result))
            return False

        result = self.hera.wait_tx_result(tx.tx_hash)
        if result.status != herapy.TxResultStatus.SUCCESS:
            print("{}Set new validators failed : nonce already used, or "
                  "invalid signature: {}".format(self.tab, result))
            return False
        else:
            print("{}{} New validators update success"
                  .format(self.tab, u'\U0001f58b'))
        return True

    def set_single_param(
        self,
        num,
        validator_indexes,
        sigs,
        contract_function,
        emoticon
    ) -> bool:
        """Call contract_function with num"""
        tx, result = self.hera.call_sc(
            self.aergo_bridge, contract_function,
            args=[num, validator_indexes, sigs]
        )
        if result.status != herapy.CommitStatus.TX_OK:
            print("{}Set new validators Tx commit failed : {}"
                  .format(self.tab, result))
            return False

        result = self.hera.wait_tx_result(tx.tx_hash)
        if result.status != herapy.TxResultStatus.SUCCESS:
            print("{}Set {} failed: nonce already used, or invalid "
                  "signature: {}".format(self.tab, contract_function, result))
            return False
        else:
            print("{}{} {} success"
                  .format(self.tab, emoticon, contract_function))
        return True
