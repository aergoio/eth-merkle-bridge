pragma solidity ^0.5.10;

import "github.com/OpenZeppelin/openzeppelin-solidity/contracts/token/ERC20/ERC20.sol#852e11c2dbb19a4000decacf1840f5e4c29c5543";


contract MintedERC20 is ERC20 {

    address creator;
    string public name;
    string public constant symbol = 'PEG';
    string public constant decimals = "Query decimals at token origin";

    constructor(string memory tokenOrigin) public {
        creator = msg.sender;
        name = tokenOrigin;
    }

    modifier onlyCreator() {
        require(msg.sender == creator, "Only creator can mint");
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