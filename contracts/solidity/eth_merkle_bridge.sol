pragma solidity ^0.5.10;

import "./minted_erc20.sol";

contract EthMerkleBridge {
    // Trie root of the opposit side bridge contract. Mints and Unlocks require a merkle proof
    // of state inclusion in this last Root.
    bytes32 public Root;
    // Height of the last block anchored
    uint public Height;
    //  2/3 of validators must sign a root update
    address[] public Validators;
    // Registers locked balances per account reference: user provides merkle proof of locked balance
    mapping(bytes => uint) public Locks;
    // Registers unlocked balances per account reference: prevents unlocking more than was burnt
    mapping(bytes => uint) public Unlocks;
    // Registers burnt balances per account reference : user provides merkle proof of burnt balance
    mapping(bytes => uint) public Burns;
    // Registers minted balances per account reference : prevents minting more than what was locked
    mapping(bytes => uint) public Mints;
    // BridgeTokens keeps track of tokens that were received through the bridge
    mapping(string => MintedERC20) public BridgeTokens;
    // MintedTokens is the same as BridgeTokens but keys and values are swapped
    mapping(address => string) public MintedTokens;
    // MintedTokens is used for preventing a minted token from being locked instead of burnt.
    // T_anchor is the anchoring periode of the bridge
    uint public T_anchor;
    // T_final is the time after which the bridge operator consideres a block finalised
    // this value is only useful if the anchored chain doesn't have LIB
    // Since Aergo has LIB it is a simple indicator for wallets.
    uint public T_final;

    // Nonce is a replay protection for validator and root updates.
    uint public Nonce;
    // ContractID is a replay protection between sidechains as the same addresses can be validators
    // on multiple chains.
    bytes32 public ContractID;

    event newMintedERC20(string indexed origin, MintedERC20 indexed addr);
    event lockEvent(IERC20 indexed token_address, string indexed receiver, uint amount);
    event unlockEvent(IERC20 indexed token_address, address indexed receiver, uint amount);
    event mintEvent(MintedERC20 indexed token_address, address indexed receiver, uint amount);
    event burnEvent(MintedERC20 indexed token_address, string indexed receiver, uint amount);
    event anchorEvent(bytes32 root, uint height);
    event newValidatorsEvent(address[] new_validators);
    event newTAnchorEvent(uint t_anchor);
    event newTFinalEvent(uint t_final);



    constructor(
        address[] memory validators,
        uint t_anchor,
        uint t_final

    ) public {
        T_anchor = t_anchor;
        T_final = t_final;
        Height = 0;
        Nonce = 0;
        Validators = validators;
        ContractID = blockhash(block.number - 1);
        Root = 0x28c5e719dc355014473f8796511132f0abdcde3fdc9114f2e7291e0752717c37;
    }

    function get_validators() public view returns (address[] memory) {
        return Validators;
    }

    function update_validators(
        address[] memory new_validators,
        uint[] memory signers,
        uint8[] memory vs,
        bytes32[] memory rs,
        bytes32[] memory ss
    ) public {
        // validators should not sign a set that is equal to the current one to prevent spamming
        bytes32 message = keccak256(abi.encodePacked(new_validators, Nonce, ContractID, "V"));
        validate_signatures(message, signers, vs, rs, ss);
        Validators = new_validators;
        Nonce += 1;
        emit newValidatorsEvent(new_validators);
    }

    function update_t_anchor(
        uint new_t_anchor,
        uint[] memory signers,
        uint8[] memory vs,
        bytes32[] memory rs,
        bytes32[] memory ss
    ) public {
        // validators should not sign a number that is equal to the current on to prevent spamming
        bytes32 message = keccak256(abi.encodePacked(new_t_anchor, Nonce, ContractID, "A"));
        validate_signatures(message, signers, vs, rs, ss);
        T_anchor = new_t_anchor;
        Nonce += 1;
        emit newTAnchorEvent(new_t_anchor);
    }

    function update_t_final(
        uint new_t_final,
        uint[] memory signers,
        uint8[] memory vs,
        bytes32[] memory rs,
        bytes32[] memory ss
    ) public {
        // validators should not sign a number that is equal to the current on to prevent spamming
        bytes32 message = keccak256(abi.encodePacked(new_t_final, Nonce, ContractID, "F"));
        validate_signatures(message, signers, vs, rs, ss);
        T_final = new_t_final;
        Nonce += 1;
        emit newTFinalEvent(new_t_final);
    }

    function set_root(
        bytes32 root,
        uint height,
        uint[] memory signers,
        uint8[] memory vs,
        bytes32[] memory rs,
        bytes32[] memory ss
    ) public {
        require(height > Height + T_anchor, "Next anchor height not reached");
        bytes32 message = keccak256(abi.encodePacked(root, height, Nonce, ContractID, "R"));
        validate_signatures(message, signers, vs, rs, ss);
        Root = root;
        Height = height;
        Nonce += 1;
        emit anchorEvent(root, height);
    }

    function validate_signatures(
        bytes32 message,
        uint[] memory signers,
        uint8[] memory vs,
        bytes32[] memory rs,
        bytes32[] memory ss
    ) public view returns (bool) {
        require(Validators.length*2 <= signers.length*3, "2/3 validators must sign");
        for (uint i = 0; i < signers.length; i++) {
        if (i > 0) {
          require(signers[i] > signers[i-1], "Provide ordered signers");
        }
        address signer = ecrecover(message, vs[i], rs[i], ss[i]);
        require(signer == Validators[signers[i]], "Signature doesn't match validator");
      }
        return true;
    }

    function lock(
        string memory receiver,
        uint amount,
        IERC20 token
    ) public returns (bool) {
        // Add locked amount to total
        bytes memory account_ref = abi.encodePacked(receiver, token);
        Locks[account_ref] += amount;
        // Pull token from owner to bridge contract (owner must set approval before calling lock)
        // using msg.sender, the owner must call lock, but we can make delegated transfers with sender
        // address as parameter.
        require(token.transferFrom(msg.sender, address(this), amount), "Failed to burn");
        emit lockEvent(token, receiver, amount);
        return true;
    }

    function unlock(
        address receiver,
        uint balance,
        IERC20 token,
        bytes32[] memory mp, // bytes[] is not yet supported so we use a bitmap of proof elements
        bytes32 bitmap,
        uint8 leaf_height
    ) public returns(bool) {
        require(balance>0, "Balance must be positive");
        bytes memory account_ref = abi.encodePacked(receiver, address(token));
        require(verify_mp("_sv_Burns-", account_ref, balance, mp, bitmap, leaf_height), "Failed to verify lock proof");
        uint unlocked_so_far = Unlocks[account_ref];
        uint to_transfer = balance - unlocked_so_far;
        require(to_transfer>0, "Burn tokens before unlocking");
        Unlocks[account_ref] = balance;
        require(token.transfer(receiver, to_transfer), "Failed to transfer unlock");
        emit unlockEvent(token, receiver, to_transfer);
        return true;
    }

    function mint(
        address receiver,
        uint balance,
        string memory token_origin,
        bytes32[] memory mp, // bytes[] is not yet supported so we use a bitmap of proof elements
        bytes32 bitmap,
        uint8 leaf_height
    ) public returns(bool) {
        require(balance>0, "Balance must be positive");
        bytes memory account_ref = abi.encodePacked(receiver, token_origin);
        require(verify_mp("_sv_Locks-", account_ref, balance, mp, bitmap, leaf_height), "Failed to verify lock proof");
        uint minted_so_far = Mints[account_ref];
        uint to_transfer = balance - minted_so_far;
        require(to_transfer>0, "Lock tokens before minting");
        MintedERC20 mint_address = BridgeTokens[token_origin];
        if (mint_address == MintedERC20(0)) {
            // first time bridging this token
            mint_address = new MintedERC20();
            BridgeTokens[token_origin] = mint_address;
            MintedTokens[address(mint_address)] = token_origin;
            emit newMintedERC20(token_origin, mint_address);
        }
        Mints[account_ref] = balance;
        require(mint_address.mint(receiver, to_transfer), "Failed to mint");
        emit mintEvent(mint_address, receiver, to_transfer);
        return true;
    }

    function burn(
        string memory receiver,
        uint amount,
        MintedERC20 mint_address
    ) public returns (bool) {
        string memory origin_address = MintedTokens[address(mint_address)];
        require(bytes(origin_address).length != 0, "cannot burn token : must have been minted by bridge");
        // Add burnt amount to total
        bytes memory account_ref = abi.encodePacked(receiver, origin_address);
        Burns[account_ref] += amount;
        // Burn token
        require(mint_address.burn(msg.sender, amount), "Failed to burn");
        emit burnEvent(mint_address, receiver, amount);
        return true;
    }

    function verify_mp(
        string memory map_name,
        bytes memory account_ref,
        uint balance,
        bytes32[] memory mp, // bytes[] is not yet supported so we use a bitmap of proof elements
        bytes32 bitmap,
        uint8 leaf_height
    ) public view returns(bool) {
        bytes32 trie_key = sha256(abi.encodePacked(map_name, account_ref));
        bytes32 trie_value = sha256(abi.encodePacked("\"", uint_to_str(balance), "\""));
        bytes32 node_hash = sha256(abi.encodePacked(trie_key, trie_value, uint8(256-leaf_height)));
        uint proof_index = 0;
        for (uint8 i = leaf_height; i>0; i--){
            if (bit_is_set(bitmap, leaf_height-i)) {
                if (bit_is_set(trie_key, i-1)) {
                    node_hash = sha256(abi.encodePacked(mp[proof_index], node_hash));
                } else {
                    node_hash = sha256(abi.encodePacked(node_hash, mp[proof_index]));
                }
                proof_index++;
            } else {
                if (bit_is_set(trie_key, i-1)) {
                    node_hash = sha256(abi.encodePacked(byte(0x00), node_hash));
                } else {
                    node_hash = sha256(abi.encodePacked(node_hash, byte(0x00)));
                }
            }
        }
        return Root == node_hash;
    }

    function bit_is_set(bytes32 bits, uint8 i) public pure returns (bool) {
        return bits[i/8]&bytes1(uint8(1)<<uint8(7-i%8)) != 0;
    }

    function uint_to_str(uint num) public pure returns(string memory) {
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