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
        ContractID = blockhash(block.number - 1);
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
}