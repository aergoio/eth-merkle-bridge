from typing import (
    Tuple,
    List,
)

from web3 import (
    Web3,
)
import logging

logger = logging.getLogger(__name__)


class EthTx():
    """ Transact with the ethereum bridge contract """

    def __init__(
        self,
        web3: Web3,
        keystore: str,
        privkey_pwd: str,
        oracle_addr: str,
        oracle_abi: str,
        eth_gas_price: int,
        t_anchor: int,
    ):
        self.eth_gas_price = eth_gas_price  # gWei
        # minimum gas price needs to be large enough for anchors to be mined
        # quickly
        self.min_gas_price = eth_gas_price
        self.t_anchor = t_anchor
        self.web3 = web3

        self.eth_oracle = self.web3.eth.contract(
            address=oracle_addr,
            abi=oracle_abi
        )

        privkey = self.web3.eth.account.decrypt(keystore, privkey_pwd)
        self.proposer_acct = self.web3.eth.account.from_key(privkey)

        logger.info("\"Proposer Address: %s\"", self.proposer_acct.address)

    def change_gas_price(self, ratio):
        """ Change the gas price by ratio.
            For example, set ratio = 1.4 to raise by 40%
        """
        max_gas_price = 70
        new_gas_price = self.eth_gas_price * ratio
        if (new_gas_price > self.min_gas_price
                and new_gas_price < max_gas_price):
            self.eth_gas_price = new_gas_price
            logger.info("\"Changed gas price to: %s\"", self.eth_gas_price)

    def new_state_anchor(
        self,
        root: bytes,
        next_anchor_height: int,
        validator_indexes: List[int],
        sigs: List[bytes],
    ) -> None:
        """Anchor a new root on Ethereum"""
        vs, rs, ss = self.prepare_rsv(sigs)
        construct_txn = self.eth_oracle.functions.newStateAnchor(
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
        receipt = self.web3.eth.waitForTransactionReceipt(
            tx_hash, timeout=300, poll_latency=1)

        if receipt.status == 1:
            logger.info(
                "\"\u2693 Anchor success, \u23F0 wait until next anchor "
                "time: %ss...\"", self.t_anchor
            )
            logger.info("\"\u26fd Eth gas used: %s\"", receipt.gasUsed)
        else:
            logger.warning(
                "\"Anchor failed: already anchored, or invalid "
                "signature: %s\"", receipt
            )

    def new_state_and_bridge_anchor(
        self,
        root: bytes,
        next_anchor_height: int,
        validator_indexes: List[int],
        sigs: List[bytes],
        bridge_contract_proto: bytes,
        merkle_proof: List[bytes],
        bitmap: bytes,
        leaf_height: int
    ) -> None:
        """Anchor a new root on Ethereum"""
        vs, rs, ss = self.prepare_rsv(sigs)
        construct_txn = self.eth_oracle.functions.newStateAndBridgeAnchor(
            root, next_anchor_height, validator_indexes, vs, rs, ss,
            bridge_contract_proto, merkle_proof, bitmap, leaf_height
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
        receipt = self.web3.eth.waitForTransactionReceipt(
            tx_hash, timeout=300, poll_latency=1)

        if receipt.status == 1:
            logger.info(
                "\"\u2693 Anchor success, \u23F0 wait until next anchor "
                "time: %ss...\"", self.t_anchor
            )
            logger.info("\"\u26fd Eth gas used: %s\"", receipt.gasUsed)
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
        receipt = self.web3.eth.waitForTransactionReceipt(
            tx_hash, timeout=300, poll_latency=1)

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
        receipt = self.web3.eth.waitForTransactionReceipt(
            tx_hash, timeout=300, poll_latency=1)

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
        receipt = self.web3.eth.waitForTransactionReceipt(
            tx_hash, timeout=300, poll_latency=1)

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
        sigs: List[bytes]
    ) -> Tuple[List[int], List[str], List[str]]:
        """ Format signature for solidity ecrecover """
        vs, rs, ss = [], [], []
        for sig in sigs:
            vs.append(self.web3.toInt(sig[-1]))
            rs.append(self.web3.toHex(sig[:32]))
            ss.append(self.web3.toHex(sig[32:64]))
        return vs, rs, ss

    def set_oracle(self, new_oracle, validator_indexes, sigs):
        """Update oracle on chain"""
        vs, rs, ss = self.prepare_rsv(sigs)
        construct_txn = self.eth_oracle.functions.oracleUpdate(
            new_oracle, validator_indexes, vs, rs, ss
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
        receipt = self.web3.eth.waitForTransactionReceipt(
            tx_hash, timeout=300, poll_latency=1)

        if receipt.status == 1:
            logger.info("\"\U0001f58b Set new oracle update success\"")
            return True
        else:
            logger.warning(
                "\"Set new oracle failed: nonce already used, or "
                "invalid signature: %s\"", receipt
            )
            return False
