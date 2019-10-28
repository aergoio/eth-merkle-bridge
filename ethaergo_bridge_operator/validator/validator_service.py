from getpass import getpass
import hashlib

from web3._utils.encoding import (
    pad_bytes,
)
from eth_utils import (
    keccak,
)

from ethaergo_bridge_operator.bridge_operator_pb2_grpc import (
    BridgeOperatorServicer,
)
from ethaergo_bridge_operator.bridge_operator_pb2 import (
    Approval,
)
from ethaergo_bridge_operator.validator.data_sources import (
    DataSources,
)
from ethaergo_bridge_operator.validator.bridge_status import (
    check_bridge_status,
)
from ethaergo_bridge_operator.validator.eth_signer import (
    EthSigner,
)
from ethaergo_bridge_operator.validator.aergo_signer import (
    AergoSigner,
)
from ethaergo_bridge_operator.op_utils import (
    load_config_data,
)
from ethaergo_bridge_operator.validator import (
    logger,
)

log_template = \
    '{\"val_index\": %s, \"signed\": %s, \"type\": \"%s\", '\
    '\"value\": %s, \"destination\": \"%s\"'
success_log_template = log_template + ', \"nonce\": %s}'
error_log_template = log_template + ', \"error\": \"%s\"}'


class ValidatorService(BridgeOperatorServicer):
    """Validates anchors for the bridge proposer.

    The validatorService and onchain bridge contracts are designed
    so that validators don't need to care about which proposer is
    calling them, validators will sign anything that is correct so that
    there can be multiple proposers.

    """

    def __init__(
        self,
        config_file_path: str,
        aergo_net: str,
        eth_net: str,
        privkey_name: str = None,
        privkey_pwd: str = None,
        validator_index: int = 0,
        auto_update: bool = False,
        root_path: str = './'
    ) -> None:
        """ Initialize parameters of the bridge validator"""
        self.auto_update = auto_update
        self.data_sources = DataSources(config_file_path, aergo_net, eth_net)
        config_data = load_config_data(config_file_path)
        self.validator_index = validator_index
        self.aergo_net = aergo_net
        self.eth_net = eth_net
        self.aergo_id, self.eth_id = check_bridge_status(
            config_data, aergo_net, eth_net, auto_update)

        if privkey_name is None:
            privkey_name = 'validator'
        if privkey_pwd is None:
            privkey_pwd = getpass("Decrypt Aergo and Ethereum accounts '{}'\n"
                                  "Password: ".format(privkey_name))
        self.eth_signer = EthSigner(
            root_path, config_data, privkey_name, privkey_pwd)
        self.aergo_signer = AergoSigner(
            root_path, config_data, privkey_name, privkey_pwd)
        # record private key for signing EthAnchor
        logger.info(
            "\"Aergo validator Address: %s\"", self.aergo_signer.address)

        # record private key for signing AergoAnchor
        logger.info(
            "\"Ethereum validator Address: %s\"", self.eth_signer.address)

    def GetAergoAnchorSignature(self, anchor, context):
        """ Verifies an aergo anchor and signs it to be broadcasted on ethereum
            aergo and ethereum nodes must be trusted.

        Note:
            Anchoring service has priority over settings update because it can
            take time to gather signatures for settings update or a validator
            may not be aware settings have changed.
            So the current onchain bridge settings are queried every time.
        """
        err_msg = self.data_sources.is_valid_aergo_anchor(anchor)
        if err_msg is not None:
            logger.warning(
                error_log_template, self.validator_index, "false",
                "\u2693 anchor", self.eth_net, err_msg
            )
            return Approval(error=err_msg)

        # sign anchor and return approval
        msg_bytes = anchor.root + anchor.height.to_bytes(32, byteorder='big') \
            + anchor.destination_nonce.to_bytes(32, byteorder='big') \
            + self.eth_id \
            + bytes("R", 'utf-8')
        h = keccak(msg_bytes)
        sig = self.eth_signer.sign(h)
        approval = Approval(
            address=self.eth_signer.address, sig=bytes(sig.signature))
        logger.info(
            success_log_template, self.validator_index, "true",
            "\u2693 anchor",
            "{{\"root\": \"0x{}\", \"height\": {}}}"
            .format(anchor.root.hex(), anchor.height),
            self.eth_net, anchor.destination_nonce
        )
        return approval

    def GetEthAnchorSignature(self, anchor, context):
        """ Verifies an ethereum anchor and signs it to be broadcasted on aergo
            aergo and ethereum nodes must be trusted.

        Note:
            Anchoring service has priority over settings update because it can
            take time to gather signatures for settings update or a validator
            may not be aware settings have changed.
            So the current onchain bridge settings are queries every time.

        """
        err_msg = self.data_sources.is_valid_eth_anchor(anchor)
        if err_msg is not None:
            logger.warning(
                error_log_template, self.validator_index, "false",
                "\u2693 anchor", self.aergo_net, err_msg
            )
            return Approval(error=err_msg)

        # sign anchor and return approval
        msg = bytes(
            anchor.root.hex() + ',' + str(anchor.height)
            + str(anchor.destination_nonce) + self.aergo_id + "R",
            'utf-8')
        h = hashlib.sha256(msg).digest()
        sig = self.aergo_signer.sign(h)
        approval = Approval(address=self.aergo_signer.address, sig=sig)
        logger.info(
            success_log_template, self.validator_index, "true",
            "\u2693 anchor",
            "{{\"root\": \"0x{}\", \"height\": {}}}"
            .format(anchor.root.hex(), anchor.height),
            self.aergo_net, anchor.destination_nonce
        )
        return approval

    def GetEthTAnchorSignature(self, tempo_msg, context):
        """Get a vote(signature) from the validator to update the t_anchor
        setting in the Aergo bridge contract bridging to Ethereum

        """
        if not self.auto_update:
            return Approval(error="Setting update not enabled")
        err_msg = self.data_sources.is_valid_eth_t_anchor(tempo_msg)
        if err_msg is not None:
            logger.warning(
                error_log_template, self.validator_index, "false",
                "\u231B t_anchor", self.aergo_net, err_msg
            )
            return Approval(error=err_msg)

        return self.sign_eth_tempo(tempo_msg, 't_anchor', "A")

    def GetEthTFinalSignature(self, tempo_msg, context):
        """Get a vote(signature) from the validator to update the t_final
        setting in the Aergo bridge contract bridging to Ethereum

        """
        if not self.auto_update:
            return Approval(error="Setting update not enabled")
        err_msg = self.data_sources.is_valid_eth_t_final(tempo_msg)
        if err_msg is not None:
            logger.warning(
                error_log_template, self.validator_index, "false",
                "\u231B t_final", self.aergo_net, err_msg
            )
            return Approval(error=err_msg)

        return self.sign_eth_tempo(tempo_msg, 't_final', "F")

    def sign_eth_tempo(self, tempo_msg, tempo_str, tempo_id):
        # sign anchor and return approval
        msg = bytes(
            str(tempo_msg.tempo) + str(tempo_msg.destination_nonce)
            + self.aergo_id + tempo_id, 'utf-8'
        )
        h = hashlib.sha256(msg).digest()
        sig = self.aergo_signer.sign(h)
        approval = Approval(address=self.aergo_signer.address, sig=sig)
        logger.info(
            success_log_template, self.validator_index, "true",
            "\u231B " + tempo_str, tempo_msg.tempo, self.aergo_net,
            tempo_msg.destination_nonce
        )
        return approval

    def GetAergoTAnchorSignature(self, tempo_msg, context):
        """Get a vote(signature) from the validator to update the t_anchor
        setting in the Ethereum bridge contract bridging to Aergo

        """
        if not self.auto_update:
            return Approval(error="Setting update not enabled")
        err_msg = self.data_sources.is_valid_aergo_t_anchor(tempo_msg)
        if err_msg is not None:
            logger.warning(
                error_log_template, self.validator_index, "false",
                "\u231B t_anchor", self.eth_net, err_msg
            )
            return Approval(error=err_msg)
        return self.sign_aergo_tempo(tempo_msg, 't_anchor', 'A')

    def GetAergoTFinalSignature(self, tempo_msg, context):
        """Get a vote(signature) from the validator to update the t_final
        setting in the Ethereum bridge contract bridging to Aergo

        """
        if not self.auto_update:
            return Approval(error="Setting update not enabled")
        err_msg = self.data_sources.is_valid_aergo_t_final(tempo_msg)
        if err_msg is not None:
            logger.warning(
                error_log_template, self.validator_index, "false",
                "\u231B t_final", self.eth_net, err_msg
            )
            return Approval(error=err_msg)
        return self.sign_aergo_tempo(tempo_msg, 't_final', 'F')

    def sign_aergo_tempo(self, tempo_msg, tempo_str, tempo_id):
        # sign anchor and return approval
        msg_bytes = tempo_msg.tempo.to_bytes(32, byteorder='big') \
            + tempo_msg.destination_nonce.to_bytes(32, byteorder='big') \
            + self.eth_id \
            + bytes(tempo_id, 'utf-8')
        h = keccak(msg_bytes)
        sig = self.eth_signer.sign(h)
        approval = Approval(
            address=self.eth_signer.address, sig=bytes(sig.signature))
        logger.info(
            success_log_template, self.validator_index, "true",
            "\u231B " + tempo_str, tempo_msg.tempo, self.eth_net,
            tempo_msg.destination_nonce
        )
        return approval

    def GetEthValidatorsSignature(self, val_msg, context):
        """Get a vote(signature) from the validator to update the set of
        validators in the Aergo bridge contract bridging to Ethereum

        """
        if not self.auto_update:
            return Approval(error="Setting update not enabled")
        err_msg = self.data_sources.is_valid_eth_validators(val_msg)
        if err_msg is not None:
            logger.warning(
                error_log_template, self.validator_index, "false",
                "\U0001f58b validator set", self.aergo_net, err_msg
            )
            return Approval(error=err_msg)

        # sign validators
        data = ""
        for val in val_msg.validators:
            data += val
        data += str(val_msg.destination_nonce) + self.aergo_id + "V"
        data_bytes = bytes(data, 'utf-8')
        h = hashlib.sha256(data_bytes).digest()
        sig = self.aergo_signer.sign(h)
        approval = Approval(address=self.aergo_signer.address, sig=sig)
        logger.info(
            success_log_template, self.validator_index, "true",
            "\U0001f58b validator set", val_msg.validators, self.aergo_net,
            val_msg.destination_nonce
        )
        return approval

    def GetAergoValidatorsSignature(self, val_msg, context):
        """Get a vote(signature) from the validator to update the set of
        validators in the Ethereum bridge contract bridging to Aergo

        """
        if not self.auto_update:
            return Approval(error="Setting update not enabled")
        err_msg = self.data_sources.is_valid_aergo_validators(val_msg)
        if err_msg is not None:
            logger.warning(
                error_log_template, self.validator_index, "false",
                "\U0001f58b validator set", self.eth_net, err_msg
            )
            return Approval(error=err_msg)

        # sign validators
        concat_vals = b''
        for val in val_msg.validators:
            concat_vals += pad_bytes(b'\x00', 32, bytes.fromhex(val[2:]))
        msg_bytes = concat_vals \
            + val_msg.destination_nonce.to_bytes(32, byteorder='big') \
            + self.eth_id \
            + bytes("V", 'utf-8')
        h = keccak(msg_bytes)
        sig = self.eth_signer.sign(h)
        approval = Approval(
            address=self.eth_signer.address, sig=bytes(sig.signature))
        logger.info(
            success_log_template, self.validator_index, "true",
            "\U0001f58b validator set", val_msg.validators, self.eth_net,
            val_msg.destination_nonce
        )
        return approval

    def GetAergoUnfreezeFeeSignature(self, new_fee_msg, context):
        """Get a vote(signature) from the validator to update the unfreezeFee
        setting in the Aergo bridge contract bridging to Ethereum

        """
        if not self.auto_update:
            return Approval(error="Setting update not enabled")
        err_msg = self.data_sources.is_valid_unfreeze_fee(new_fee_msg)
        if err_msg is not None:
            logger.warning(
                error_log_template, self.validator_index, "false",
                "\U0001f4a7 unfreeze fee", self.aergo_net, err_msg
            )
            return Approval(error=err_msg)

        # sign anchor and return approval
        msg = bytes(
            str(new_fee_msg.fee) + str(new_fee_msg.destination_nonce)
            + self.aergo_id + "UF", 'utf-8'
        )
        h = hashlib.sha256(msg).digest()
        sig = self.aergo_signer.sign(h)
        approval = Approval(address=self.aergo_signer.address, sig=sig)
        logger.info(
            success_log_template, self.validator_index, "true",
            "\U0001f4a7 unfreeze fee", new_fee_msg.fee, self.aergo_net,
            new_fee_msg.destination_nonce
        )
        return approval
