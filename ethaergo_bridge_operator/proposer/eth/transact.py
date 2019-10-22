from typing import (
    Tuple,
    List,
)

from web3 import (
    Web3,
)


class EthTx():
    """ Transact with the ethereum bridge contract """

    def __init__(
        self,
        web3: Web3,
        encrypted_key: str,
        privkey_pwd: str,
        eth_bridge_address: str,
        eth_abi: str,
        eth_gas_price: int,
        t_anchor: int,
        tab: str
    ):
        self.eth_gas_price = eth_gas_price  # gWei
        self.t_anchor = t_anchor
        self.tab = tab
        self.web3 = web3

        self.eth_bridge = self.web3.eth.contract(
            address=eth_bridge_address,
            abi=eth_abi
        )

        privkey = self.web3.eth.account.decrypt(encrypted_key, privkey_pwd)
        self.proposer_acct = self.web3.eth.account.from_key(privkey)

        print("  > Proposer Address: {}".format(self.proposer_acct.address))

    def new_anchor(
        self,
        root: bytes,
        next_anchor_height: int,
        validator_indexes: List[int],
        sigs: List[str],
    ) -> None:
        """Anchor a new root on Ethereum"""
        vs, rs, ss = self.prepare_rsv(sigs)
        construct_txn = self.eth_bridge.functions.newAnchor(
            root, next_anchor_height, validator_indexes, vs, rs, ss
        ).buildTransaction({
            'chainId': self.web3.eth.chainId,
            'from': self.proposer_acct.address,
            'nonce': self.web3.eth.getTransactionCount(
                self.proposer_acct.address
            ),
            'gas': 500000,
            'gasPrice': self.web3.toWei(self.eth_gas_price, 'gwei')
        })
        signed = self.proposer_acct.sign_transaction(construct_txn)
        tx_hash = self.web3.eth.sendRawTransaction(signed.rawTransaction)
        receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)

        if receipt.status == 1:
            print("{0}{1} Anchor success,\n{0}{2} wait until next anchor "
                  "time: {3}s...".format(self.tab, u'\u2693', u'\u23F0',
                                         self.t_anchor))
            print("{}\u26fd Gas used: {}".format(self.tab, receipt.gasUsed))
        else:
            print("{}Anchor failed: already anchored, or invalid "
                  "signature: {}".format(self.tab, receipt))

    def set_validators(self, new_validators, validator_indexes, sigs):
        """Update validators on chain"""
        vs, rs, ss = self.prepare_rsv(sigs)
        construct_txn = self.eth_bridge.functions.validatorsUpdate(
            new_validators, validator_indexes, vs, rs, ss
        ).buildTransaction({
            'chainId': self.web3.eth.chainId,
            'from': self.proposer_acct.address,
            'nonce': self.web3.eth.getTransactionCount(
                self.proposer_acct.address
            ),
            'gas': 500000,
            'gasPrice': self.web3.toWei(self.eth_gas_price, 'gwei')
        })
        signed = self.proposer_acct.sign_transaction(construct_txn)
        tx_hash = self.web3.eth.sendRawTransaction(signed.rawTransaction)
        receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)

        if receipt.status == 1:
            print("{}{} Set new validators update success"
                  .format(self.tab, u'\U0001f58b'))
            return True
        else:
            print("{}Set new validators failed: nonce already used, or "
                  "invalid signature: {}".format(self.tab, receipt))
            return False

    def set_t_anchor(self, t_anchor, validator_indexes, sigs):
        """Update t_anchor on chain"""
        vs, rs, ss = self.prepare_rsv(sigs)
        construct_txn = self.eth_bridge.functions.tAnchorUpdate(
            t_anchor, validator_indexes, vs, rs, ss
        ).buildTransaction({
            'chainId': self.web3.eth.chainId,
            'from': self.proposer_acct.address,
            'nonce': self.web3.eth.getTransactionCount(
                self.proposer_acct.address
            ),
            'gas': 108036,
            'gasPrice': self.web3.toWei(self.eth_gas_price, 'gwei')
        })
        signed = self.proposer_acct.sign_transaction(construct_txn)
        tx_hash = self.web3.eth.sendRawTransaction(signed.rawTransaction)
        receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)

        if receipt.status == 1:
            print("{}{} tAnchorUpdate success".format(self.tab, u'\u231B'))
            return True
        else:
            print("{}tAnchorUpdate failed: nonce already used, or "
                  "invalid signature: {}".format(self.tab, receipt))
            return False

    def set_t_final(self, t_final, validator_indexes, sigs):
        """Update t_final on chain"""
        vs, rs, ss = self.prepare_rsv(sigs)
        construct_txn = self.eth_bridge.functions.tFinalUpdate(
            t_final, validator_indexes, vs, rs, ss
        ).buildTransaction({
            'chainId': self.web3.eth.chainId,
            'from': self.proposer_acct.address,
            'nonce': self.web3.eth.getTransactionCount(
                self.proposer_acct.address
            ),
            'gas': 108036,
            'gasPrice': self.web3.toWei(self.eth_gas_price, 'gwei')
        })
        signed = self.proposer_acct.sign_transaction(construct_txn)
        tx_hash = self.web3.eth.sendRawTransaction(signed.rawTransaction)
        receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)

        if receipt.status == 1:
            print("{}{} tFinalUpdate success".format(self.tab, u'\u231B'))
            return True
        else:
            print("{}tFinalUpdate failed: nonce already used, or "
                  "invalid signature: {}".format(self.tab, receipt))
            return False

    def prepare_rsv(
        self,
        sigs: List[str]
    ) -> Tuple[List[int], List[str], List[str]]:
        """ Format signature for solidity ecrecover """
        vs, rs, ss = [], [], []
        for sig in sigs:
            vs.append(self.web3.toInt(sig[-1]))
            rs.append(self.web3.toHex(sig[:32]))
            ss.append(self.web3.toHex(sig[32:64]))
        return vs, rs, ss
