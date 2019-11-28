pragma solidity ^0.5.10;

import "./eth_merkle_bridge.sol";

contract Oracle {
    // Global State root included in block headers
    bytes32 public _anchorRoot;
    // Height of the last block anchored
    uint public _anchorHeight;
    // _tAnchor is the anchoring periode: sets a minimal delay between anchors to prevent spamming
    // and give time to applications to build merkle proof for their data.
    uint public _tAnchor;
    // _tFinal is the time after which the validators considere a block finalised
    // this value is only useful if the anchored chain doesn't have LIB
    // Since Aergo has LIB it is a simple indicator for wallets.
    uint public _tFinal;
    //  2/3 of validators must sign to interact
    address[] public _validators;
    // _nonce is a replay protection for anchors and settings update
    uint public _nonce;
    // _contractId is a replay protection between sidechains as the same addresses can be validators
    // on multiple chains.
    bytes32 public _contractId;
    // address of the bridge contract being controled
    EthMerkleBridge public _bridge;
    // General Aergo state trie key of the bridge contract on Aergo blockchain
    bytes32 public _destinationBridgeKey;

    event newValidatorsEvent(address[] validators);
    event anchorEvent(bytes32 root, uint height);

    // Create a new oracle contract
    // @param   validators - array of Ethereum addresses
    // @param   bridge - address of already deployed bridge contract
    // @param   destinationBridgeKey - trie key of destination bridge contract in Aergo state trie
    constructor(
        address[] memory validators,
        EthMerkleBridge bridge,
        bytes32 destinationBridgeKey,
        uint tAnchor,
        uint tFinal
    ) public {
        _validators = validators;
        _tAnchor = tAnchor;
        _tFinal = tFinal;
        _bridge = bridge;
        _destinationBridgeKey = destinationBridgeKey;
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
        // _t_anchor prevents anchor spamming just like the _t_anchor in the bridge contract.
        // also useful info for wallets.
        _tAnchor = tAnchor;
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
        // _tfinal is redundant with the value stored in the bridge: just a useful information for apps.
        _tFinal = tFinal;
        _bridge.tFinalUpdate(tFinal);
    }

    // Register a new anchor
    // @param   root - Aergo blocks state root
    // @param   height - block height of root
    // @param   signers - array of signer indexes
    // @param   vs, rs, ss - array of signatures matching signers indexes
    function newStateAnchor(
        bytes32 root,
        uint height,
        uint[] memory signers,
        uint8[] memory vs,
        bytes32[] memory rs,
        bytes32[] memory ss
    ) public {
        require(height > _anchorHeight + _tAnchor, "Next anchor height not reached");
        bytes32 message = keccak256(abi.encodePacked(root, height, _nonce, _contractId, "R"));
        validateSignatures(message, signers, vs, rs, ss);
        _nonce += 1;
        _anchorRoot = root;
        _anchorHeight = height;
        emit anchorEvent(root, height);
    }

    // Register a new bridge anchor
    // @param   proto - Proto bytes of the serialized contract account
    // @param   mp - merkle proof of inclusion of proto serialized account in general trie
    // @param   bitmap - bitmap of non default nodes in the merkle proof
    // @param   leafHeight - height of leaf containing the value in the state SMT
    function newBridgeAnchor(
        bytes memory proto,
        bytes32[] memory mp, // bytes[] is not yet supported so we use a bitmap of proof elements
        bytes32 bitmap,
        uint8 leafHeight
    ) public {
        bytes32 root = parseRootFromProto(proto);
        bytes32 accountHash = sha256(proto);
        require(verifyMp(_destinationBridgeKey, accountHash, mp, bitmap, leafHeight), "Failed to verify bridge state inside general state");
        _bridge.newAnchor(root, _anchorHeight);
    }

    // Register a new state anchor and update the bridge anchor
    // @param   stateRoot - Aergo general state root
    // @param   height - block height of root
    // @param   signers - array of signer indexes
    // @param   vs, rs, ss - array of signatures matching signers indexes
    // @param   proto - Proto bytes of the serialized contract account
    // @param   mp - merkle proof of inclusion of proto serialized account in general trie
    // @param   bitmap - bitmap of non default nodes in the merkle proof
    // @param   leafHeight - height of leaf containing the value in the state SMT
    function newStateAndBridgeAnchor(
        bytes32 stateRoot,
        uint height,
        uint[] memory signers,
        uint8[] memory vs,
        bytes32[] memory rs,
        bytes32[] memory ss,
        bytes memory proto,
        bytes32[] memory mp, // bytes[] is not yet supported so we use a bitmap of proof elements
        bytes32 bitmap,
        uint8 leafHeight
    ) public {
        newStateAnchor(stateRoot, height, signers, vs, rs, ss);
        newBridgeAnchor(proto, mp, bitmap, leafHeight);
    }

    // Aergo State Trie Merkle proof verification
    // @param   trieKey - General trie key storing the bridge contract account
    // @param   trieValue - Hash of the contract account state
    // @param   mp - merkle proof of inclusion of accountRef, balance in _anchorRoot
    // @param   bitmap - bitmap of non default nodes in the merkle proof
    // @param   leafHeight - height of leaf containing the value in the state SMT
    function verifyMp(
        bytes32 trieKey,
        bytes32 trieValue,
        bytes32[] memory mp, // bytes[] is not yet supported so we use a bitmap of proof elements
        bytes32 bitmap,
        uint8 leafHeight
    ) public view returns(bool) {
        bytes32 nodeHash = sha256(abi.encodePacked(trieKey, trieValue, uint8(256-leafHeight)));
        uint proofIndex = 0;
        for (uint8 i = leafHeight; i>0; i--){
            if (bitIsSet(bitmap, leafHeight-i)) {
                if (bitIsSet(trieKey, i-1)) {
                    nodeHash = sha256(abi.encodePacked(mp[proofIndex], nodeHash));
                } else {
                    nodeHash = sha256(abi.encodePacked(nodeHash, mp[proofIndex]));
                }
                proofIndex++;
            } else {
                if (bitIsSet(trieKey, i-1)) {
                    nodeHash = sha256(abi.encodePacked(byte(0x00), nodeHash));
                } else {
                    nodeHash = sha256(abi.encodePacked(nodeHash, byte(0x00)));
                }
            }
        }
        return _anchorRoot == nodeHash;
    }

    // check if the ith bit is set in bytes
    // @param   bits - bytesin which we check the ith bit
    // @param   i - index of bit to check
    function bitIsSet(bytes32 bits, uint8 i) public pure returns (bool) {
        return bits[i/8]&bytes1(uint8(1)<<uint8(7-i%8)) != 0;
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

    // Parse a proto serialized contract account state to extract the storage root
    // @param proto - serialized proto account
    function parseRootFromProto(bytes memory proto) public pure returns(bytes32) {
        /*
            Aergo account state object:
            message State {
                uint64 nonce = 1;
                bytes balance = 2;
                bytes codeHash = 3;
                bytes storageRoot = 4;
                uint64 sqlRecoveryPoint = 5;
            }
            https://developers.google.com/protocol-buffers/docs/encoding

            +--------------+-----------+----------+--------------+
            | field number | wire type | tag(hex) |   tag(bin)   |
            |       1      |     0     |   0x08   |   0000 1000  |
            |       2      |     2     |   0x12   |   0001 0010  |
            |       3      |     2     |   0x1a   |   0001 1010  |
            |       4      |     2     |   0x22   |   0010 0010  |
            |       5      |     0     |   0x2a   |   0010 1010  |
            +--------------+-----------+----------+--------------+

            Contracts can have 0 balance and 0 nonce, so their tags 0x08 and 0x12 are not always present
            in the serialized state.
        */
        uint index = 0; // keep track of byte index while steping through the proto bytes.

        // parse uint64 nonce = 1
        if (proto[index] == 0x08) {
            index++;
            for (index; index<proto.length;) {
                // 0x80 = 128 => check if the first bit is 0 or 1.
                // The first bit of the last byte of the varint nb is 0
                if (proto[index] < 0x80) {
                    index++;
                    break;
                }
                index++;
            }
        }

        // parse bytes balance = 2
        if (proto[index] == 0x12) {
            index++;
            // calculate varint nb of bytes used to encode balance
            // the balance is encoded with 32 bytes (0x20) maximum so the length takes a single byte
            require(proto[index] <= 0x20, "Invalid balance length");
            uint balanceLength = uint8(proto[index]);
            index += balanceLength + 1;
        }

        // parse bytes codeHash = 3
        require(proto[index] == 0x1a, "Invalid codeHash proto tag");
        index++;
        require(proto[index] == 0x20, "Invalid codeHash length");
        index += 33;

        // parse bytes storageRoot = 4
        require(proto[index] == 0x22, "Invalid storageRoot proto tag");
        index++;
        require(proto[index] == 0x20, "Invalid storageRoot length");
        index++; // start of storageRoot bytes
        // extrack storageRoot
        bytes32 storageRoot;
        assembly {
            // https://github.com/GNSPS/solidity-bytes-utils/blob/e3d1f6831e870896a5cd5efe5e87efbbcb86e2c4/contracts/BytesLib.sol#L381
            storageRoot := mload(add(add(proto, 0x20), index))
        }
        return storageRoot;
    }
}
