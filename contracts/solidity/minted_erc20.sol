pragma solidity ^0.5.10;

import "github.com/OpenZeppelin/openzeppelin-solidity/contracts/token/ERC20/ERC20.sol#852e11c2dbb19a4000decacf1840f5e4c29c5543";


contract MintedERC20 is ERC20 {

    address _creator;
    //string public _name;
    string public constant _symbol = 'PEG';
    uint8 public constant _decimals = 18;

    constructor() public {
        _creator = msg.sender;
        //_name = originAddress; storing the name causes payload too large eip170.
        // we can make a contract factory for creating MintedERC20,
        // but nice to have a single contract if possible.
    }

    modifier onlyCreator() {
        require(msg.sender == _creator, "Only creator can mint");
        _;
    }

    function mint(address receiver, uint amount) public onlyCreator returns (bool) {
        _mint(receiver, amount);
        return true;
    }

    function burn(address account, uint amount) public onlyCreator returns (bool) {
        _burn(account, amount);
        return true;
    }

}