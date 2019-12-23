from functools import (
    partial,
)
import grpc
import hashlib
from multiprocessing.dummy import (
    Pool,
)

from typing import (
    Tuple,
    Optional,
    List,
    Any,
    Dict
)

import aergo.herapy as herapy
from aergo.herapy.utils.signature import (
    verify_sig,
)

from ethaergo_bridge_operator.bridge_operator_pb2_grpc import (
    BridgeOperatorStub,
)
from ethaergo_bridge_operator.bridge_operator_pb2 import (
    Anchor,
    NewValidators,
    NewTempo,
    NewUnfreezeFee,
    NewOracle,

)
from ethaergo_bridge_operator.op_utils import (
    query_aergo_validators,
    query_aergo_id,
)
from ethaergo_bridge_operator.proposer.exceptions import (
    ValidatorMajorityError,
)
import logging

logger = logging.getLogger(__name__)


class AergoValConnect():
    """ Connect to Validators validating data to be anchored on
    Aergo.

    """

    def __init__(
        self,
        config_data: Dict,
        hera: herapy.Aergo,
        aergo_oracle: str,
    ):
        self.hera = hera
        self.config_data = config_data
        self.aergo_oracle = aergo_oracle
        self.aergo_id = query_aergo_id(self.hera, self.aergo_oracle)

        current_validators = query_aergo_validators(
            self.hera, self.aergo_oracle)
        logger.info("\"Validators: %s\"", current_validators)

        # create all channels with validators
        self.channels: List[grpc._channel.Channel] = []
        self.stubs: List[BridgeOperatorStub] = []
        assert len(current_validators) == len(self.config_data['validators']), \
            "Validators in config file must match bridge validators " \
            "when starting (current validators connection needed to make "\
            "updates).\nExpected validators: {}".format(current_validators)
        for i, validator in enumerate(self.config_data['validators']):
            assert current_validators[i] == validator['addr'], \
                "Validators in config file must match bridge validators " \
                "when starting (current validators connection needed to make "\
                "updates).\nExpected validators: {}".format(current_validators)
            ip = validator['ip']
            channel = grpc.insecure_channel(ip)
            stub = BridgeOperatorStub(channel)
            self.channels.append(channel)
            self.stubs.append(stub)

        self.pool = Pool(len(self.stubs))

    def get_anchor_signatures(
        self,
        root: str,
        merge_height: int,
        nonce: int,
    ) -> Tuple[List[str], List[int]]:
        """ Query all validators and gather 2/3 of their signatures. """

        # messages to get signed
        msg_str = root + ',' + str(merge_height) + str(nonce) \
            + self.aergo_id + "R"
        msg = bytes(msg_str, 'utf-8')
        h = hashlib.sha256(msg).digest()

        anchor = Anchor(
            root=bytes.fromhex(root), height=merge_height,
            destination_nonce=nonce
        )

        # get validator signatures and verify sig in worker
        validator_indexes = [i for i in range(len(self.stubs))]
        worker = partial(self.get_signature_worker, "GetEthAnchorSignature",
                         anchor, h)
        approvals = self.pool.map(worker, validator_indexes)

        sigs, validator_indexes = self.extract_signatures(approvals)

        return sigs, validator_indexes

    def get_signature_worker(
        self,
        rpc_service: str,
        request,
        h: bytes,
        idx: int
    ) -> Optional[Any]:
        """ Get a validator's (index) signature and verify it"""
        try:
            approval = getattr(self.stubs[idx], rpc_service)(request)
        except grpc.RpcError as e:
            logger.warning(
                "\"Failed to connect to validator %s (RpcError)\"", idx)
            logger.warning(e)
            return None
        if approval.error:
            logger.warning("\"%s by validator %s\"", approval.error, idx)
            return None
        if approval.address != self.config_data['validators'][idx]['addr']:
            # check nothing is wrong with validator address
            logger.warning(
                "\"Unexpected validator %s address: %s\"", idx,
                approval.address
            )
            return None
        # validate signature
        if not verify_sig(h, approval.sig, approval.address):
            logger.warning("\"Invalid signature from validator %s\"", idx)
            return None
        return approval

    def extract_signatures(
        self,
        approvals: List[Any]
    ) -> Tuple[List[str], List[int]]:
        """ Convert signatures to hex string and keep 2/3 of them."""
        sigs, validator_indexes = [], []
        for i, approval in enumerate(approvals):
            if approval is not None:
                # convert to hex string for lua
                sigs.append('0x' + approval.sig.hex())
                # +1 for lua indexes
                validator_indexes.append(i+1)
        total_validators = len(self.config_data['validators'])
        if 3 * len(sigs) < 2 * total_validators:
            raise ValidatorMajorityError()
        # slice 2/3 of total validators
        two_thirds = ((total_validators * 2) // 3
                      + ((total_validators * 2) % 3 > 0))
        return sigs[:two_thirds], validator_indexes[:two_thirds]

    def get_new_validators_signatures(self, validators):
        """Request approvals of validators for the new validator set."""
        nonce = int(
            self.hera.query_sc_state(
                self.aergo_oracle, ["_sv__nonce"]).var_proofs[0].value
        )
        new_validators_msg = NewValidators(
            validators=validators, destination_nonce=nonce)
        data = ""
        for val in validators:
            data += val
        data += str(nonce) + self.aergo_id + "V"
        data_bytes = bytes(data, 'utf-8')
        h = hashlib.sha256(data_bytes).digest()
        # get validator signatures and verify sig in worker
        validator_indexes = [i for i in range(len(self.stubs))]
        worker = partial(
            self.get_signature_worker, "GetEthValidatorsSignature",
            new_validators_msg, h
        )
        approvals = self.pool.map(worker, validator_indexes)
        sigs, validator_indexes = self.extract_signatures(approvals)
        return sigs, validator_indexes

    def get_tempo_signatures(self, tempo, rpc_service, tempo_id):
        """Request approvals of validators for the new t_anchor or t_final."""
        nonce = int(
            self.hera.query_sc_state(
                self.aergo_oracle, ["_sv__nonce"]).var_proofs[0].value
        )
        new_tempo_msg = NewTempo(tempo=tempo, destination_nonce=nonce)
        msg = bytes(
            str(tempo) + str(nonce) + self.aergo_id + tempo_id,
            'utf-8'
        )
        h = hashlib.sha256(msg).digest()
        validator_indexes = [i for i in range(len(self.stubs))]
        worker = partial(
            self.get_signature_worker, rpc_service,
            new_tempo_msg, h
        )
        approvals = self.pool.map(worker, validator_indexes)
        sigs, validator_indexes = self.extract_signatures(approvals)
        return sigs, validator_indexes

    def get_unfreeze_fee_signatures(self, fee):
        """Request approvals of validators for the new t_anchor or t_final."""
        nonce = int(
            self.hera.query_sc_state(
                self.aergo_oracle, ["_sv__nonce"]).var_proofs[0].value
        )
        new_fee_msg = NewUnfreezeFee(fee=fee, destination_nonce=nonce)
        msg = bytes(
            str(fee) + str(nonce) + self.aergo_id + "UF",
            'utf-8'
        )
        h = hashlib.sha256(msg).digest()
        validator_indexes = [i for i in range(len(self.stubs))]
        worker = partial(
            self.get_signature_worker, "GetAergoUnfreezeFeeSignature",
            new_fee_msg, h
        )
        approvals = self.pool.map(worker, validator_indexes)
        sigs, validator_indexes = self.extract_signatures(approvals)
        return sigs, validator_indexes

    def use_new_validators(self, config_data):
        """Update connections to validators after a successful update
        of bridge validators with the validators in the config file.

        """
        self.config_data = config_data
        self.channels = []
        self.stubs = []
        for validator in self.config_data['validators']:
            ip = validator['ip']
            channel = grpc.insecure_channel(ip)
            stub = BridgeOperatorStub(channel)
            self.channels.append(channel)
            self.stubs.append(stub)

        self.pool = Pool(len(self.stubs))

    def get_new_oracle_signatures(self, oracle):
        """Request approvals of validators for the new oracle."""
        nonce = int(
            self.hera.query_sc_state(
                self.aergo_oracle, ["_sv__nonce"]).var_proofs[0].value
        )
        new_oracle_msg = NewOracle(
            oracle=oracle, destination_nonce=nonce)
        data = oracle + str(nonce) + self.aergo_id + "O"
        data_bytes = bytes(data, 'utf-8')
        h = hashlib.sha256(data_bytes).digest()
        # get validator signatures and verify sig in worker
        validator_indexes = [i for i in range(len(self.stubs))]
        worker = partial(
            self.get_signature_worker, "GetEthOracleSignature",
            new_oracle_msg, h
        )
        approvals = self.pool.map(worker, validator_indexes)
        sigs, validator_indexes = self.extract_signatures(approvals)
        return sigs, validator_indexes
