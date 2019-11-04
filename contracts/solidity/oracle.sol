pragma solidity ^0.5.10;

import "./eth_merkle_bridge.sol";

contract Oracle {
    //  2/3 of validators must sign to interact
    address[] public _validators;
    // _nonce is a replay protection for anchors and settings update
    uint public _nonce;
    // _contractId is a replay protection between sidechains as the same addresses can be validators
    // on multiple chains.
    bytes32 public _contractId;
    // address of the bridge contract being controled
    EthMerkleBridge public _bridge;

    event newValidatorsEvent(address[] validators);

    constructor(
        address[] memory validators,
        EthMerkleBridge bridge
    ) public {
        _validators = validators;
        _bridge = bridge;
        _contractId = keccak256(abi.encodePacked(blockhash(block.number - 1), this));
    }

    function getValidators() public view returns (address[] memory) {
        return _validators;
    }


    // Register a new set of validators
    // @param   validators - signers of state anchors
    // @param   signers - array of signer indexes
    // @param   vs, rs, ss - array of signatures matching signers indexes
    function validatorsUpdate(
        address[] memory validators,
        uint[] memory signers,
        uint8[] memory vs,
        bytes32[] memory rs,
        bytes32[] memory ss
    ) public {
        // validators should not sign a set that is equal to the current one to prevent spamming
        bytes32 message = keccak256(abi.encodePacked(validators, _nonce, _contractId, "V"));
        validateSignatures(message, signers, vs, rs, ss);
        _validators = validators;
        _nonce += 1;
        emit newValidatorsEvent(validators);
    }

    // Replace the oracle of the bridge
    // @param   oracle - new contract that will replace this one for controlling the bridge
    // @param   signers - array of signer indexes
    // @param   vs, rs, ss - array of signatures matching signers indexes
    function oracleUpdate(
        address oracle,
        uint[] memory signers,
        uint8[] memory vs,
        bytes32[] memory rs,
        bytes32[] memory ss
    ) public {
        // validators should not sign a set that is equal to the current one to prevent spamming
        bytes32 message = keccak256(abi.encodePacked(oracle, _nonce, _contractId, "O"));
        validateSignatures(message, signers, vs, rs, ss);
        _nonce += 1;
        // this contract now doesnt have controle over the bridge anymore
        _bridge.oracleUpdate(oracle);
    }

    // Register new anchoring periode
    // @param   tAnchor - new anchoring periode
    // @param   signers - array of signer indexes
    // @param   vs, rs, ss - array of signatures matching signers indexes
    function tAnchorUpdate(
        uint tAnchor,
        uint[] memory signers,
        uint8[] memory vs,
        bytes32[] memory rs,
        bytes32[] memory ss
    ) public {
        // validators should not sign a number that is equal to the current one to prevent spamming
        bytes32 message = keccak256(abi.encodePacked(tAnchor, _nonce, _contractId, "A"));
        validateSignatures(message, signers, vs, rs, ss);
        _nonce += 1;
        _bridge.tAnchorUpdate(tAnchor);
    }

    // Register new finality of anchored chain
    // @param   tFinal - new finality of anchored chain
    // @param   signers - array of signer indexes
    // @param   vs, rs, ss - array of signatures matching signers indexes
    function tFinalUpdate(
        uint tFinal,
        uint[] memory signers,
        uint8[] memory vs,
        bytes32[] memory rs,
        bytes32[] memory ss
    ) public {
        // validators should not sign a number that is equal to the current one to prevent spamming
        bytes32 message = keccak256(abi.encodePacked(tFinal, _nonce, _contractId, "F"));
        validateSignatures(message, signers, vs, rs, ss);
        _nonce += 1;
        _bridge.tFinalUpdate(tFinal);
    }

    // Register a new anchor
    // @param   root - Aergo storage root
    // @param   height - block height of root
    // @param   signers - array of signer indexes
    // @param   vs, rs, ss - array of signatures matching signers indexes
    function newAnchor(
        bytes32 root,
        uint height,
        uint[] memory signers,
        uint8[] memory vs,
        bytes32[] memory rs,
        bytes32[] memory ss
    ) public {
        bytes32 message = keccak256(abi.encodePacked(root, height, _nonce, _contractId, "R"));
        validateSignatures(message, signers, vs, rs, ss);
        _nonce += 1;
        _bridge.newAnchor(root, height);
    }

    // Check 2/3 validators signed message hash
    // @param   message - message signed (hash of data)
    // @param   signers - array of signer indexes
    // @param   vs, rs, ss - array of signatures matching signers indexes
    function validateSignatures(
        bytes32 message,
        uint[] memory signers,
        uint8[] memory vs,
        bytes32[] memory rs,
        bytes32[] memory ss
    ) public view returns (bool) {
        require(_validators.length*2 <= signers.length*3, "2/3 validators must sign");
        for (uint i = 0; i < signers.length; i++) {
            if (i > 0) {
                require(signers[i] > signers[i-1], "Provide ordered signers");
            }
            address signer = ecrecover(message, vs[i], rs[i], ss[i]);
            require(signer == _validators[signers[i]], "Signature doesn't match validator");
        }
        return true;
    }
}
