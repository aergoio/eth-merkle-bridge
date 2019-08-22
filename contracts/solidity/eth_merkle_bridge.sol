pragma solidity ^0.5.10;

import "./minted_erc20.sol";

contract EthMerkleBridge {
    // Trie root of the opposit side bridge contract. Mints and Unlocks require a merkle proof
    // of state inclusion in this last Root.
    bytes32 public _anchorRoot;
    // Height of the last block anchored
    uint public _anchorHeight;
    //  2/3 of validators must sign a root update
    address[] public _validators;
    // Registers locked balances per account reference: user provides merkle proof of locked balance
    mapping(bytes => uint) public _locks;
    // Registers unlocked balances per account reference: prevents unlocking more than was burnt
    mapping(bytes => uint) public _unlocks;
    // Registers burnt balances per account reference : user provides merkle proof of burnt balance
    mapping(bytes => uint) public _burns;
    // Registers minted balances per account reference : prevents minting more than what was locked
    mapping(bytes => uint) public _mints;
    // _bridgeTokens keeps track of tokens that were received through the bridge
    mapping(string => MintedERC20) public _bridgeTokens;
    // _mintedTokens is the same as _bridgeTokens but keys and values are swapped
    // _mintedTokens is used for preventing a minted token from being locked instead of burnt.
    mapping(address => string) public _mintedTokens;
    // _tAnchor is the anchoring periode of the bridge
    uint public _tAnchor;
    // _tFinal is the time after which the bridge operator consideres a block finalised
    // this value is only useful if the anchored chain doesn't have LIB
    // Since Aergo has LIB it is a simple indicator for wallets.
    uint public _tFinal;
    // _nonce is a replay protection for validator and root updates.
    uint public _nonce;
    // _contractId is a replay protection between sidechains as the same addresses can be validators
    // on multiple chains.
    bytes32 public _contractId;

    event newMintedERC20(string indexed origin, MintedERC20 indexed addr);
    event lockEvent(IERC20 indexed tokenAddress, string indexed receiver, uint amount);
    event unlockEvent(IERC20 indexed tokenAddress, address indexed receiver, uint amount);
    event mintEvent(MintedERC20 indexed tokenAddress, address indexed receiver, uint amount);
    event burnEvent(MintedERC20 indexed tokenAddress, string indexed receiver, uint amount);
    event anchorEvent(bytes32 root, uint height);
    event newValidatorsEvent(address[] validators);
    event newTAnchorEvent(uint tAnchor);
    event newTFinalEvent(uint tFinal);

    constructor(
        address[] memory validators,
        uint tAnchor,
        uint tFinal

    ) public {
        _tAnchor = tAnchor;
        _tFinal = tFinal;
        _validators = validators;
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
        _tAnchor = tAnchor;
        _nonce += 1;
        emit newTAnchorEvent(tAnchor);
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
        _tFinal = tFinal;
        _nonce += 1;
        emit newTFinalEvent(tFinal);
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
        require(height > _anchorHeight + _tAnchor, "Next anchor height not reached");
        bytes32 message = keccak256(abi.encodePacked(root, height, _nonce, _contractId, "R"));
        validateSignatures(message, signers, vs, rs, ss);
        _anchorRoot = root;
        _anchorHeight = height;
        _nonce += 1;
        emit anchorEvent(root, height);
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

    // lock tokens in the bridge contract
    // @param   token - token locked to transfer
    // @param   amount - amount of tokens to send
    // @param   receiver - Aergo address receiver accross the bridge
    function lock(
        IERC20 token,
        uint amount,
        string memory receiver
    ) public returns (bool) {
        // Add locked amount to total
        bytes memory accountRef = abi.encodePacked(receiver, token);
        _locks[accountRef] += amount;
        // Pull token from owner to bridge contract (owner must set approval before calling lock)
        // using msg.sender, the owner must call lock, but we can make delegated transfers with sender
        // address as parameter.
        require(token.transferFrom(msg.sender, address(this), amount), "Failed to burn");
        emit lockEvent(token, receiver, amount);
        return true;
    }

    // unlock tokens burnt on Aergo
    // anybody can unlock, the receiver is the account who's burnt balance is recorded
    // @param   receiver - address of receiver
    // @param   balance - total balance of tokens burnt on Aergo
    // @param   token - address of token to unlock
    // @param   mp - merkle proof of inclusion of burnt balance on Aergo
    // @param   bitmap - bitmap of non default nodes in the merkle proof
    // @param   leafHeight - height of leaf containing the value in the state SMT
    function unlock(
        address receiver,
        uint balance,
        IERC20 token,
        bytes32[] memory mp, // bytes[] is not yet supported so we use a bitmap of proof elements
        bytes32 bitmap,
        uint8 leafHeight
    ) public returns(bool) {
        require(balance>0, "Balance must be positive");
        bytes memory accountRef = abi.encodePacked(receiver, address(token));
        require(verifyMp("_sv__burns-", accountRef, balance, mp, bitmap, leafHeight), "Failed to verify lock proof");
        uint unlockedSoFar = _unlocks[accountRef];
        uint amountToTransfer = balance - unlockedSoFar;
        require(amountToTransfer>0, "Burn tokens before unlocking");
        _unlocks[accountRef] = balance;
        require(token.transfer(receiver, amountToTransfer), "Failed to transfer unlock");
        emit unlockEvent(token, receiver, amountToTransfer);
        return true;
    }

    // mint a token locked on Aergo
    // anybody can mint, the receiver is the account who's locked balance is recorded
    // @param   receiver - address of receiver
    // @param   balance - total balance of tokens locked on Aergo
    // @param   tokenOrigin - Aergo address of token locked
    // @param   mp - merkle proof of inclusion of locked balance on Aergo
    // @param   bitmap - bitmap of non default nodes in the merkle proof
    // @param   leafHeight - height of leaf containing the value in the state SMT
    function mint(
        address receiver,
        uint balance,
        string memory tokenOrigin,
        bytes32[] memory mp, // bytes[] is not yet supported so we use a bitmap of proof elements
        bytes32 bitmap,
        uint8 leafHeight
    ) public returns(bool) {
        require(balance>0, "Balance must be positive");
        bytes memory accountRef = abi.encodePacked(receiver, tokenOrigin);
        require(verifyMp("_sv__locks-", accountRef, balance, mp, bitmap, leafHeight), "Failed to verify lock proof");
        uint mintedSoFar = _mints[accountRef];
        uint amountToTransfer = balance - mintedSoFar;
        require(amountToTransfer>0, "Lock tokens before minting");
        MintedERC20 mintAddress = _bridgeTokens[tokenOrigin];
        if (mintAddress == MintedERC20(0)) {
            // first time bridging this token
            mintAddress = new MintedERC20();
            _bridgeTokens[tokenOrigin] = mintAddress;
            _mintedTokens[address(mintAddress)] = tokenOrigin;
            emit newMintedERC20(tokenOrigin, mintAddress);
        }
        _mints[accountRef] = balance;
        require(mintAddress.mint(receiver, amountToTransfer), "Failed to mint");
        emit mintEvent(mintAddress, receiver, amountToTransfer);
        return true;
    }

    // burn a pegged token
    // @param   receiver - Aergo address
    // @param   amount - number of tokens to burn
    // @param   mintAddress - address of pegged token to burn
    function burn(
        string memory receiver,
        uint amount,
        MintedERC20 mintAddress
    ) public returns (bool) {
        string memory originAddress = _mintedTokens[address(mintAddress)];
        require(bytes(originAddress).length != 0, "cannot burn token : must have been minted by bridge");
        // Add burnt amount to total
        bytes memory accountRef = abi.encodePacked(receiver, originAddress);
        _burns[accountRef] += amount;
        // Burn token
        require(mintAddress.burn(msg.sender, amount), "Failed to burn");
        emit burnEvent(mintAddress, receiver, amount);
        return true;
    }

    // Aergo State Trie Merkle proof verification
    // @param   mapName - name of Lua map variable storing locked/burnt balances
    // @param   accountRef - key in mapName to record an account's token balance
    // @param   balance - balance recorded in accountRef of mapName
    // @param   mp - merkle proof of inclusion of accountRef, balance in _anchorRoot
    // @param   bitmap - bitmap of non default nodes in the merkle proof
    // @param   leafHeight - height of leaf containing the value in the state SMT
    function verifyMp(
        string memory mapName,
        bytes memory accountRef,
        uint balance,
        bytes32[] memory mp, // bytes[] is not yet supported so we use a bitmap of proof elements
        bytes32 bitmap,
        uint8 leafHeight
    ) public view returns(bool) {
        bytes32 trieKey = sha256(abi.encodePacked(mapName, accountRef));
        bytes32 trieValue = sha256(abi.encodePacked("\"", uintToString(balance), "\""));
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

    // Lua contract don't store real bytes of uin so converting to string in necessary
    // @param   num - convert uint to string type : 1234 -> "1234"
    function uintToString(uint num) public pure returns(string memory) {
        // https://github.com/oraclize/ethereum-api/blob/6fb6e887e7b95c496fd723a7c62ce40551f8028a/oraclizeAPI_0.5.sol#L1041
        if (num == 0) {
            return "0";
        }
        uint j = num;
        uint len;
        while (j != 0) {
            len++;
            j /= 10;
        }
        bytes memory bstr = new bytes(len);
        uint k = len - 1;
        while (num != 0) {
            bstr[k--] = byte(uint8(48 + num % 10));
            num /= 10;
        }
        return string(bstr);
    }
}