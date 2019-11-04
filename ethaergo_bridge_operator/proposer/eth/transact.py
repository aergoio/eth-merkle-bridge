from typing import (
    Tuple,
    List,
)

from web3 import (
    Web3,
)
import logging

logger = logging.getLogger("proposer.eth")


class EthTx():
    """ Transact with the ethereum bridge contract """

    def __init__(
        self,
        web3: Web3,
        encrypted_key: str,
        privkey_pwd: str,
        oracle_addr: str,
        oracle_abi: str,
        eth_gas_price: int,
        t_anchor: int,
    ):
        self.eth_gas_price = eth_gas_price  # gWei
        self.t_anchor = t_anchor
        self.web3 = web3

        self.eth_oracle = self.web3.eth.contract(
            address=oracle_addr,
            abi=oracle_abi
        )

        privkey = self.web3.eth.account.decrypt(encrypted_key, privkey_pwd)
        self.proposer_acct = self.web3.eth.account.from_key(privkey)

        logger.info("\"Proposer Address: %s\"", self.proposer_acct.address)

    def new_anchor(
        self,
        root: bytes,
        next_anchor_height: int,
        validator_indexes: List[int],
        sigs: List[str],
    ) -> None:
        """Anchor a new root on Ethereum"""
        vs, rs, ss = self.prepare_rsv(sigs)
        construct_txn = self.eth_oracle.functions.newAnchor(
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
            logger.info(
                "\"\u2693 Anchor success, \u23F0 wait until next anchor "
                "time: %ss...\"", self.t_anchor
            )
            logger.info("\"\u26fd Gas used: %s\"", receipt.gasUsed)
        else:
            logger.warning(
                "\"Anchor failed: already anchored, or invalid "
                "signature: %s\"", receipt
            )

    def set_validators(self, new_validators, validator_indexes, sigs):
        """Update validators on chain"""
        vs, rs, ss = self.prepare_rsv(sigs)
        construct_txn = self.eth_oracle.functions.validatorsUpdate(
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
            logger.info("\"\U0001f58b Set new validators update success\"")
            return True
        else:
            logger.warning(
                "\"Set new validators failed: nonce already used, or "
                "invalid signature: %s\"", receipt
            )
            return False

    def set_t_anchor(self, t_anchor, validator_indexes, sigs):
        """Update t_anchor on chain"""
        vs, rs, ss = self.prepare_rsv(sigs)
        construct_txn = self.eth_oracle.functions.tAnchorUpdate(
            t_anchor, validator_indexes, vs, rs, ss
        ).buildTransaction({
            'chainId': self.web3.eth.chainId,
            'from': self.proposer_acct.address,
            'nonce': self.web3.eth.getTransactionCount(
                self.proposer_acct.address
            ),
            'gas': 200000,
            'gasPrice': self.web3.toWei(self.eth_gas_price, 'gwei')
        })
        signed = self.proposer_acct.sign_transaction(construct_txn)
        tx_hash = self.web3.eth.sendRawTransaction(signed.rawTransaction)
        receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)

        if receipt.status == 1:
            logger.info("\"\u231B tAnchorUpdate success\"")
            return True
        else:
            logger.warning(
                "\"tAnchorUpdate failed: nonce already used, or "
                "invalid signature: %s\"", receipt
            )
            return False

    def set_t_final(self, t_final, validator_indexes, sigs):
        """Update t_final on chain"""
        vs, rs, ss = self.prepare_rsv(sigs)
        construct_txn = self.eth_oracle.functions.tFinalUpdate(
            t_final, validator_indexes, vs, rs, ss
        ).buildTransaction({
            'chainId': self.web3.eth.chainId,
            'from': self.proposer_acct.address,
            'nonce': self.web3.eth.getTransactionCount(
                self.proposer_acct.address
            ),
            'gas': 200000,
            'gasPrice': self.web3.toWei(self.eth_gas_price, 'gwei')
        })
        signed = self.proposer_acct.sign_transaction(construct_txn)
        tx_hash = self.web3.eth.sendRawTransaction(signed.rawTransaction)
        receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)

        if receipt.status == 1:
            logger.info("\"\u231B tFinalUpdate success\"")
            return True
        else:
            logger.warning(
                "\"tFinalUpdate failed: nonce already used, or "
                "invalid signature: %s\"", receipt
            )
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
