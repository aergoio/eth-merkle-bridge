pragma solidity ^0.5.8;

contract MerkleBridge {
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
    // Registers minted balances per account reference : prevents minting more than what was locked
    // BridgeTokens keeps track of tokens that were received through the bridge
    // MintedTokens is the same as BridgeTokens but keys and values are swapped
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
        Root = 0x1234ee76fecb7510ee28293d41dfc061bab55da402b134142105d352190a29ed;
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
        string memory asset_addr,
        bytes32[] memory mp, // bytes[] is not yet supported so we use a bitmap of proof elements
        bytes32 bitmap,
        uint8 leaf_height
    ) public returns(bool) {
        return verify_mp("_sv_Locks-", receiver, balance, asset_addr, mp, bitmap, leaf_height);
    }

    function verify_mp(
        string memory map_name,
        address receiver,
        uint balance,
        string memory asset_addr,
        bytes32[] memory mp, // bytes[] is not yet supported so we use a bitmap of proof elements
        bytes32 bitmap,
        uint8 leaf_height
    ) public view returns(bool) {
        bytes memory var_id = abi.encodePacked(map_name, addr_to_str(receiver), asset_addr);
        bytes32 trie_key = sha256(var_id);
        bytes memory value = abi.encodePacked("\"", uint_to_str(balance), "\"");
        bytes32 trie_value = sha256(value);
        bytes memory leaf = abi.encodePacked(trie_key, trie_value, uint8(256-leaf_height));
        bytes32 node_hash = sha256(leaf);
        uint proof_index = 0;
        for (uint8 i=leaf_height; i>0; i--){
            if (bit_is_set(bitmap, i-1)) {
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
    
    function test(uint8 num) public returns(bytes memory) {
        bytes memory a = abi.encodePacked(uint8(256-num));
        return a;
    }
    
    
/*
    //https://github.com/OpenZeppelin/openzeppelin-solidity/blob/master/contracts/cryptography/MerkleProof.sol
    // receiver is an address converted to utf8 string or vice versa
    // balance is a uint converted to a utf8 string or vice versa
    //https://github.com/willitscale/solidity-util/blob/master/lib/Integers.sol
    //https://ethereum.stackexchange.com/questions/10932/how-to-convert-string-to-int
    //http://remebit.com/converting-strings-to-integers-in-solidity/
    //https://www.edureka.co/community/7924/how-to-convert-int-to-string-in-solidity
    function parseAddr(string memory _a) public returns (address){
        // https://github.com/oraclize/ethereum-api/blob/6fb6e887e7b95c496fd723a7c62ce40551f8028a/oraclizeAPI_pre0.4.sol#L157
        bytes memory tmp = bytes(_a);
        uint160 iaddr = 0;
        uint8 b1;
        uint8 b2;
        for (uint i=2; i<2+2*20; i+=2){
            iaddr *= 256;
            b1 = uint8(tmp[i]);
            b2 = uint8(tmp[i+1]);
            if ((b1 >= 97)&&(b1 <= 102)) b1 -= 87;
            else if ((b1 >= 48)&&(b1 <= 57)) b1 -= 48;
            if ((b2 >= 97)&&(b2 <= 102)) b2 -= 87;
            else if ((b2 >= 48)&&(b2 <= 57)) b2 -= 48;
            iaddr += (b1*16+b2);
        }
        return address(iaddr);
    }
    
    function toString(address x) public returns (string memory) {
        bytes memory b = new bytes(20);
        for (uint i = 0; i < 20; i++)
            b[i] = byte(uint8(uint(x) / (2**(8*(19 - i)))));
        return string(b);
    }

    function test() public returns (string memory) {
        string memory senderString = toString(msg.sender);
        return senderString;
    }
*/   
}