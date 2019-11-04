from functools import (
    partial,
)
import grpc
from multiprocessing.dummy import (
    Pool,
)

from typing import (
    Dict,
    Tuple,
    List,
    Any,
)

from web3 import (
    Web3,
)
from web3._utils.encoding import (
    pad_bytes,
)
from eth_utils import (
    keccak,
)

from ethaergo_bridge_operator.bridge_operator_pb2_grpc import (
    BridgeOperatorStub,
)
from ethaergo_bridge_operator.bridge_operator_pb2 import (
    Anchor,
    NewValidators,
    NewTempo
)
from ethaergo_bridge_operator.proposer.exceptions import (
    ValidatorMajorityError,
)
import logging

logger = logging.getLogger("proposer.eth")


class EthValConnect():
    """ Connect to Validators validating data to be anchored on
    Ethereum.

    """

    def __init__(
        self,
        config_data: Dict,
        web3: Web3,
        oracle_addr: str,
        oracle_abi: str,
    ):
        self.web3 = web3
        self.config_data = config_data

        self.eth_oracle = self.web3.eth.contract(
            address=oracle_addr,
            abi=oracle_abi
        )
        self.eth_id = self.eth_oracle.functions._contractId().call()

        current_validators = self.eth_oracle.functions.getValidators().call()
        logger.info("\"Validators: %s\"", current_validators)

        self.channels: List[grpc._channel.Channel] = []
        self.stubs: List[BridgeOperatorStub] = []
        assert len(current_validators) == len(config_data['validators']), \
            "Validators in config file must match bridge validators " \
            "when starting (current validators connection needed to make "\
            "updates).\nExpected validators: {}".format(current_validators)
        for i, validator in enumerate(config_data['validators']):
            assert current_validators[i] == validator['eth-addr'], \
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
        root: bytes,
        merge_height: int,
        nonce: int,
    ) -> Tuple[List[str], List[int]]:
        """ Query all validators and gather 2/3 of their signatures. """
        # messages to get signed
        msg_bytes = root + merge_height.to_bytes(32, byteorder='big') \
            + nonce.to_bytes(32, byteorder='big') \
            + self.eth_id \
            + bytes("R", 'utf-8')
        h = keccak(msg_bytes)

        anchor = Anchor(
            root=root, height=merge_height, destination_nonce=nonce
        )

        # get validator signatures and verify sig in worker
        validator_indexes = [i for i in range(len(self.stubs))]
        worker = partial(
            self.get_signature_worker, "GetAergoAnchorSignature", anchor, h)
        approvals = self.pool.map(worker, validator_indexes)

        sigs, validator_indexes = self.extract_signatures(approvals)

        return sigs, validator_indexes

    def get_signature_worker(
        self,
        rpc_service: str,
        request,
        h: bytes,
        idx: int
    ):
        """ Get a validator's (index) signature and verify it"""
        try:
            approval = getattr(self.stubs[idx], rpc_service)(request)
        except grpc.RpcError:
            logger.warning(
                "\"Failed to connect to validator %s (RpcError)\"", idx)
            return None
        if approval.error:
            logger.warning("\"%s\"", approval.error)
            return None
        if approval.address != self.config_data['validators'][idx]['eth-addr']:
            # check nothing is wrong with validator address
            logger.warning(
                "\"Unexpected validator %s address: %s\"", idx,
                approval.address
            )
            return None
        # validate signature
        if not approval.address == self.web3.eth.account.recoverHash(
            h, signature=approval.sig
        ):
            logger.warning("\"Invalid signature from validator %s\"", idx)
            return None
        return approval

    def extract_signatures(
        self,
        approvals: List[Any]
    ) -> Tuple[List[str], List[int]]:
        """Keep 2/3 of validator signatures (minimum to anchor)"""
        sigs, validator_indexes = [], []
        for i, approval in enumerate(approvals):
            if approval is not None:
                sigs.append(approval.sig)
                validator_indexes.append(i)
        total_validators = len(self.config_data['validators'])
        if 3 * len(sigs) < 2 * total_validators:
            raise ValidatorMajorityError()
        # slice 2/3 of total validators
        two_thirds = ((total_validators * 2) // 3
                      + ((total_validators * 2) % 3 > 0))
        return sigs[:two_thirds], validator_indexes[:two_thirds]

    def get_new_validators_signatures(self, validators):
        """Request approvals of validators for the new validator set."""
        nonce = self.eth_oracle.functions._nonce().call()
        new_validators_msg = NewValidators(
            validators=validators, destination_nonce=nonce)
        concat_vals = b''
        for val in validators:
            concat_vals += pad_bytes(b'\x00', 32, bytes.fromhex(val[2:]))
        msg_bytes = concat_vals \
            + nonce.to_bytes(32, byteorder='big') \
            + self.eth_id \
            + bytes("V", 'utf-8')
        h = keccak(msg_bytes)
        # get validator signatures and verify sig in worker
        validator_indexes = [i for i in range(len(self.stubs))]
        worker = partial(
            self.get_signature_worker, "GetAergoValidatorsSignature",
            new_validators_msg, h
        )
        approvals = self.pool.map(worker, validator_indexes)
        sigs, validator_indexes = self.extract_signatures(approvals)
        return sigs, validator_indexes

    def get_tempo_signatures(self, tempo, rpc_service, tempo_id):
        """Request approvals of validators for the new t_anchor or t_final."""
        nonce = self.eth_oracle.functions._nonce().call()
        new_tempo_msg = NewTempo(
            tempo=tempo, destination_nonce=nonce)
        msg_bytes = tempo.to_bytes(32, byteorder='big') \
            + nonce.to_bytes(32, byteorder='big') \
            + self.eth_id \
            + bytes(tempo_id, 'utf-8')
        h = keccak(msg_bytes)
        validator_indexes = [i for i in range(len(self.stubs))]
        worker = partial(
            self.get_signature_worker, rpc_service,
            new_tempo_msg, h
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
