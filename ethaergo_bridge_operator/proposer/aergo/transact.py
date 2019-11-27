from typing import (
    List,
)

import aergo.herapy as herapy
import logging

logger = logging.getLogger(__name__)


class AergoTx():
    """ Transact with the aergo bridge contract """

    def __init__(
        self,
        hera: herapy.Aergo,
        encrypted_key: str,
        privkey_pwd: str,
        aergo_oracle: str,
        aergo_gas_price: int,
        t_anchor: int,
        eth_block_time: int,
    ):
        self.aergo_gas_price= aergo_gas_price
        self.t_anchor = t_anchor
        self.eth_block_time = eth_block_time
        self.hera = hera
        self.aergo_oracle = aergo_oracle

        self.hera.import_account(encrypted_key, privkey_pwd)
        logger.info(
            "\"Proposer Address: %s\"", self.hera.account.address)

    def new_state_anchor(
        self,
        root: str,
        next_anchor_height: int,
        validator_indexes: List[int],
        sigs: List[str],
    ) -> None:
        """Anchor a new state root on chain"""
        tx, result = self.hera.call_sc(
            self.aergo_oracle, "newStateAnchor",
            args=[root, next_anchor_height, validator_indexes, sigs]
        )
        if result.status != herapy.CommitStatus.TX_OK:
            logger.warning(
                "\"Anchor on aergo Tx commit failed : %s\"", result.json())
            return

        result = self.hera.wait_tx_result(tx.tx_hash)
        if result.status != herapy.TxResultStatus.SUCCESS:
            logger.warning(
                "\"Anchor failed: already anchored, or invalid "
                "signature: %s\"", result.json()
            )
        else:
            logger.info(
                "\"\u2693 Anchor success, \u23F0 wait until next anchor "
                "time: %ss...\"",
                self.t_anchor * self.eth_block_time
            )
            logger.info("\"\u26fd Aergo Fee: %s\"", result.fee_used)

    def new_state_and_bridge_anchor(
        self,
        stateRoot: str,
        next_anchor_height: int,
        validator_indexes: List[int],
        sigs: List[str],
        bridge_contract_state: List[str],
        merkle_proof: List[str]
    ) -> None:
        """Anchor a new state root and update bridge anchor on chain"""
        bridge_nonce, bridge_balance, bridge_root, bridge_code_hash = \
            bridge_contract_state
        tx, result = self.hera.call_sc(
            self.aergo_oracle, "newStateAndBridgeAnchor",
            args=[stateRoot, next_anchor_height, validator_indexes, sigs,
                  bridge_nonce, bridge_balance, bridge_root, bridge_code_hash,
                  merkle_proof]
        )
        if result.status != herapy.CommitStatus.TX_OK:
            logger.warning(
                "\"Anchor on aergo Tx commit failed : %s\"", result.json())
            return

        result = self.hera.wait_tx_result(tx.tx_hash)
        if result.status != herapy.TxResultStatus.SUCCESS:
            logger.warning(
                "\"Anchor failed: already anchored, or invalid "
                "signature: %s\"", result.json()
            )
        else:
            logger.info(
                "\"\u2693 Anchor success, \u23F0 wait until next anchor "
                "time: %ss...\"",
                self.t_anchor * self.eth_block_time
            )
            logger.info("\"\u26fd Aergo Fee: %s\"", result.fee_used)

    def set_validators(self, new_validators, validator_indexes, sigs):
        """Update validators on chain"""
        tx, result = self.hera.call_sc(
            self.aergo_oracle, "validatorsUpdate",
            args=[new_validators, validator_indexes, sigs]
        )
        if result.status != herapy.CommitStatus.TX_OK:
            logger.warning(
                "\"Set new validators Tx commit failed : %s\"",
                result.json()
            )
            return False

        result = self.hera.wait_tx_result(tx.tx_hash)
        if result.status != herapy.TxResultStatus.SUCCESS:
            logger.warning(
                "\"Set new validators failed : nonce already used, or "
                "invalid signature: %s\"", result.json()
            )
            return False
        else:
            logger.info("\"\U0001f58b New validators update success\"")
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
            self.aergo_oracle, contract_function,
            args=[num, validator_indexes, sigs]
        )
        if result.status != herapy.CommitStatus.TX_OK:
            logger.warning(
                "\"Set %s Tx commit failed : %s\"",
                contract_function, result.json()
            )
            return False

        result = self.hera.wait_tx_result(tx.tx_hash)
        if result.status != herapy.TxResultStatus.SUCCESS:
            logger.warning(
                "\"Set %s failed: nonce already used, or invalid "
                "signature: %s\"",
                contract_function, result.json()
            )
            return False
        else:
            logger.info(
                "\"%s %s success\"", emoticon, contract_function)
        return True

    def set_oracle(self, new_oracle, validator_indexes, sigs):
        """Update oracle on chain"""
        tx, result = self.hera.call_sc(
            self.aergo_oracle, "oracleUpdate",
            args=[new_oracle, validator_indexes, sigs]
        )
        if result.status != herapy.CommitStatus.TX_OK:
            logger.warning(
                "\"Set new oracle Tx commit failed : %s\"",
                result.json()
            )
            return False

        result = self.hera.wait_tx_result(tx.tx_hash)
        if result.status != herapy.TxResultStatus.SUCCESS:
            logger.warning(
                "\"Set new oracle failed : nonce already used, or "
                "invalid signature: %s\"", result.json()
            )
            return False
        else:
            logger.info("\"\U0001f58b New oracle update success\"")
        return True
