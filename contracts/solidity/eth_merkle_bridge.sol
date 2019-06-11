pragma solidity ^0.5.0;

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
    // Registers unlocked balances per account reference: prevents unlocking more than was burnt
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
    bytes32 public ContractID;
    // ContractID is a replay protection between sidechains as the same addresses can be validators
    // on multiple chains.
    
    event newMintedERC20(string indexed origin, MintedERC20 indexed addr);
    event mintEvent(MintedERC20 indexed token_address, address indexed receiver, uint amount);
    event burnEvent(MintedERC20 indexed token_address, string indexed receiver, uint amount);


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
        //ContractID = blockhash(block.number - 1);
        Root = 0x28c5e719dc355014473f8796511132f0abdcde3fdc9114f2e7291e0752717c37;
    }

    function get_validators() public view returns (address[] memory) {
        return Validators;
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

    function mint(
        address receiver,
        uint balance,
        string memory token_origin,
        bytes32[] memory mp, // bytes[] is not yet supported so we use a bitmap of proof elements
        bytes32 bitmap,
        uint8 leaf_height
    ) public returns(bool) {
        require(balance>0, "Balance must be positive");
        bytes memory account_ref = abi.encodePacked(addr_to_str(receiver), token_origin);
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
        for (uint8 i=leaf_height; i>0; i--){
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

    function addr_to_str(address _addr) public pure returns(string memory) {
        //https://ethereum.stackexchange.com/questions/30290/conversion-of-address-to-string-in-solidity?rq=1
        bytes32 value = bytes32(uint256(_addr));
        bytes memory alphabet = "0123456789abcdef";
        bytes memory str = new bytes(40);
        for (uint i = 0; i < 20; i++) {
            str[i*2] = alphabet[uint8(value[i + 12] >> 4)];
            str[1+i*2] = alphabet[uint8(value[i + 12] & 0x0f)];
        }
        return string(str);
    }

    function bit_is_set(bytes32 bits, uint8 i) public pure returns (bool) {
        return bits[i/8]&bytes1(1<<uint8(7-i%8)) != 0;
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
    
    function test(uint8 num) public returns(bytes32) {
        bytes memory a = abi.encodePacked(byte(0x00));
        bytes32 b = sha256(a);
        return b;
    }
}