pragma solidity ^0.5.0;

import "github.com/OpenZeppelin/openzeppelin-solidity/contracts/token/ERC20/ERC20.sol";


contract MintedERC20 is ERC20 {

    address creator;

    constructor() public {
        creator = msg.sender;
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