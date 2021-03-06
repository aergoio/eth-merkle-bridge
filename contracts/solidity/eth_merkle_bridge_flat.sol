// Flatened contract generated by Flattener plugin in Remix
// This file can then be used to verify the eth-merkle-bridge.sol contract source
// code in Etherscan (manually or with the Etherscan - Contract Verification plugin)

// File: github.com/OpenZeppelin/openzeppelin-solidity/contracts/math/SafeMath.sol

pragma solidity ^0.5.0;

/**
 * @dev Wrappers over Solidity's arithmetic operations with added overflow
 * checks.
 *
 * Arithmetic operations in Solidity wrap on overflow. This can easily result
 * in bugs, because programmers usually assume that an overflow raises an
 * error, which is the standard behavior in high level programming languages.
 * `SafeMath` restores this intuition by reverting the transaction when an
 * operation overflows.
 *
 * Using this library instead of the unchecked operations eliminates an entire
 * class of bugs, so it's recommended to use it always.
 */
library SafeMath {
    /**
     * @dev Returns the addition of two unsigned integers, reverting on
     * overflow.
     *
     * Counterpart to Solidity's `+` operator.
     *
     * Requirements:
     * - Addition cannot overflow.
     */
    function add(uint256 a, uint256 b) internal pure returns (uint256) {
        uint256 c = a + b;
        require(c >= a, "SafeMath: addition overflow");

        return c;
    }

    /**
     * @dev Returns the subtraction of two unsigned integers, reverting on
     * overflow (when the result is negative).
     *
     * Counterpart to Solidity's `-` operator.
     *
     * Requirements:
     * - Subtraction cannot overflow.
     */
    function sub(uint256 a, uint256 b) internal pure returns (uint256) {
        return sub(a, b, "SafeMath: subtraction overflow");
    }

    /**
     * @dev Returns the subtraction of two unsigned integers, reverting with custom message on
     * overflow (when the result is negative).
     *
     * Counterpart to Solidity's `-` operator.
     *
     * Requirements:
     * - Subtraction cannot overflow.
     *
     * _Available since v2.4.0._
     */
    function sub(uint256 a, uint256 b, string memory errorMessage) internal pure returns (uint256) {
        require(b <= a, errorMessage);
        uint256 c = a - b;

        return c;
    }

    /**
     * @dev Returns the multiplication of two unsigned integers, reverting on
     * overflow.
     *
     * Counterpart to Solidity's `*` operator.
     *
     * Requirements:
     * - Multiplication cannot overflow.
     */
    function mul(uint256 a, uint256 b) internal pure returns (uint256) {
        // Gas optimization: this is cheaper than requiring 'a' not being zero, but the
        // benefit is lost if 'b' is also tested.
        // See: https://github.com/OpenZeppelin/openzeppelin-contracts/pull/522
        if (a == 0) {
            return 0;
        }

        uint256 c = a * b;
        require(c / a == b, "SafeMath: multiplication overflow");

        return c;
    }

    /**
     * @dev Returns the integer division of two unsigned integers. Reverts on
     * division by zero. The result is rounded towards zero.
     *
     * Counterpart to Solidity's `/` operator. Note: this function uses a
     * `revert` opcode (which leaves remaining gas untouched) while Solidity
     * uses an invalid opcode to revert (consuming all remaining gas).
     *
     * Requirements:
     * - The divisor cannot be zero.
     */
    function div(uint256 a, uint256 b) internal pure returns (uint256) {
        return div(a, b, "SafeMath: division by zero");
    }

    /**
     * @dev Returns the integer division of two unsigned integers. Reverts with custom message on
     * division by zero. The result is rounded towards zero.
     *
     * Counterpart to Solidity's `/` operator. Note: this function uses a
     * `revert` opcode (which leaves remaining gas untouched) while Solidity
     * uses an invalid opcode to revert (consuming all remaining gas).
     *
     * Requirements:
     * - The divisor cannot be zero.
     *
     * _Available since v2.4.0._
     */
    function div(uint256 a, uint256 b, string memory errorMessage) internal pure returns (uint256) {
        // Solidity only automatically asserts when dividing by 0
        require(b > 0, errorMessage);
        uint256 c = a / b;
        // assert(a == b * c + a % b); // There is no case in which this doesn't hold

        return c;
    }

    /**
     * @dev Returns the remainder of dividing two unsigned integers. (unsigned integer modulo),
     * Reverts when dividing by zero.
     *
     * Counterpart to Solidity's `%` operator. This function uses a `revert`
     * opcode (which leaves remaining gas untouched) while Solidity uses an
     * invalid opcode to revert (consuming all remaining gas).
     *
     * Requirements:
     * - The divisor cannot be zero.
     */
    function mod(uint256 a, uint256 b) internal pure returns (uint256) {
        return mod(a, b, "SafeMath: modulo by zero");
    }

    /**
     * @dev Returns the remainder of dividing two unsigned integers. (unsigned integer modulo),
     * Reverts with custom message when dividing by zero.
     *
     * Counterpart to Solidity's `%` operator. This function uses a `revert`
     * opcode (which leaves remaining gas untouched) while Solidity uses an
     * invalid opcode to revert (consuming all remaining gas).
     *
     * Requirements:
     * - The divisor cannot be zero.
     *
     * _Available since v2.4.0._
     */
    function mod(uint256 a, uint256 b, string memory errorMessage) internal pure returns (uint256) {
        require(b != 0, errorMessage);
        return a % b;
    }
}

// File: github.com/OpenZeppelin/openzeppelin-solidity/contracts/token/ERC20/IERC20.sol

pragma solidity ^0.5.0;

/**
 * @dev Interface of the ERC20 standard as defined in the EIP. Does not include
 * the optional functions; to access them see {ERC20Detailed}.
 */
interface IERC20 {
    /**
     * @dev Returns the amount of tokens in existence.
     */
    function totalSupply() external view returns (uint256);

    /**
     * @dev Returns the amount of tokens owned by `account`.
     */
    function balanceOf(address account) external view returns (uint256);

    /**
     * @dev Moves `amount` tokens from the caller's account to `recipient`.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * Emits a {Transfer} event.
     */
    function transfer(address recipient, uint256 amount) external returns (bool);

    /**
     * @dev Returns the remaining number of tokens that `spender` will be
     * allowed to spend on behalf of `owner` through {transferFrom}. This is
     * zero by default.
     *
     * This value changes when {approve} or {transferFrom} are called.
     */
    function allowance(address owner, address spender) external view returns (uint256);

    /**
     * @dev Sets `amount` as the allowance of `spender` over the caller's tokens.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * IMPORTANT: Beware that changing an allowance with this method brings the risk
     * that someone may use both the old and the new allowance by unfortunate
     * transaction ordering. One possible solution to mitigate this race
     * condition is to first reduce the spender's allowance to 0 and set the
     * desired value afterwards:
     * https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
     *
     * Emits an {Approval} event.
     */
    function approve(address spender, uint256 amount) external returns (bool);

    /**
     * @dev Moves `amount` tokens from `sender` to `recipient` using the
     * allowance mechanism. `amount` is then deducted from the caller's
     * allowance.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * Emits a {Transfer} event.
     */
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);

    /**
     * @dev Emitted when `value` tokens are moved from one account (`from`) to
     * another (`to`).
     *
     * Note that `value` may be zero.
     */
    event Transfer(address indexed from, address indexed to, uint256 value);

    /**
     * @dev Emitted when the allowance of a `spender` for an `owner` is set by
     * a call to {approve}. `value` is the new allowance.
     */
    event Approval(address indexed owner, address indexed spender, uint256 value);
}

// File: github.com/OpenZeppelin/openzeppelin-solidity/contracts/GSN/Context.sol

pragma solidity ^0.5.0;

/*
 * @dev Provides information about the current execution context, including the
 * sender of the transaction and its data. While these are generally available
 * via msg.sender and msg.data, they should not be accessed in such a direct
 * manner, since when dealing with GSN meta-transactions the account sending and
 * paying for execution may not be the actual sender (as far as an application
 * is concerned).
 *
 * This contract is only required for intermediate, library-like contracts.
 */
contract Context {
    // Empty internal constructor, to prevent people from mistakenly deploying
    // an instance of this contract, which should be used via inheritance.
    constructor () internal { }
    // solhint-disable-previous-line no-empty-blocks

    function _msgSender() internal view returns (address payable) {
        return msg.sender;
    }

    function _msgData() internal view returns (bytes memory) {
        this; // silence state mutability warning without generating bytecode - see https://github.com/ethereum/solidity/issues/2691
        return msg.data;
    }
}

// File: github.com/OpenZeppelin/openzeppelin-solidity/contracts/token/ERC20/ERC20.sol#852e11c2dbb19a4000decacf1840f5e4c29c5543

pragma solidity ^0.5.0;




/**
 * @dev Implementation of the {IERC20} interface.
 *
 * This implementation is agnostic to the way tokens are created. This means
 * that a supply mechanism has to be added in a derived contract using {_mint}.
 * For a generic mechanism see {ERC20Mintable}.
 *
 * TIP: For a detailed writeup see our guide
 * https://forum.zeppelin.solutions/t/how-to-implement-erc20-supply-mechanisms/226[How
 * to implement supply mechanisms].
 *
 * We have followed general OpenZeppelin guidelines: functions revert instead
 * of returning `false` on failure. This behavior is nonetheless conventional
 * and does not conflict with the expectations of ERC20 applications.
 *
 * Additionally, an {Approval} event is emitted on calls to {transferFrom}.
 * This allows applications to reconstruct the allowance for all accounts just
 * by listening to said events. Other implementations of the EIP may not emit
 * these events, as it isn't required by the specification.
 *
 * Finally, the non-standard {decreaseAllowance} and {increaseAllowance}
 * functions have been added to mitigate the well-known issues around setting
 * allowances. See {IERC20-approve}.
 */
contract ERC20 is Context, IERC20 {
    using SafeMath for uint256;

    mapping (address => uint256) private _balances;

    mapping (address => mapping (address => uint256)) private _allowances;

    uint256 private _totalSupply;

    /**
     * @dev See {IERC20-totalSupply}.
     */
    function totalSupply() public view returns (uint256) {
        return _totalSupply;
    }

    /**
     * @dev See {IERC20-balanceOf}.
     */
    function balanceOf(address account) public view returns (uint256) {
        return _balances[account];
    }

    /**
     * @dev See {IERC20-transfer}.
     *
     * Requirements:
     *
     * - `recipient` cannot be the zero address.
     * - the caller must have a balance of at least `amount`.
     */
    function transfer(address recipient, uint256 amount) public returns (bool) {
        _transfer(_msgSender(), recipient, amount);
        return true;
    }

    /**
     * @dev See {IERC20-allowance}.
     */
    function allowance(address owner, address spender) public view returns (uint256) {
        return _allowances[owner][spender];
    }

    /**
     * @dev See {IERC20-approve}.
     *
     * Requirements:
     *
     * - `spender` cannot be the zero address.
     */
    function approve(address spender, uint256 amount) public returns (bool) {
        _approve(_msgSender(), spender, amount);
        return true;
    }

    /**
     * @dev See {IERC20-transferFrom}.
     *
     * Emits an {Approval} event indicating the updated allowance. This is not
     * required by the EIP. See the note at the beginning of {ERC20};
     *
     * Requirements:
     * - `sender` and `recipient` cannot be the zero address.
     * - `sender` must have a balance of at least `amount`.
     * - the caller must have allowance for `sender`'s tokens of at least
     * `amount`.
     */
    function transferFrom(address sender, address recipient, uint256 amount) public returns (bool) {
        _transfer(sender, recipient, amount);
        _approve(sender, _msgSender(), _allowances[sender][_msgSender()].sub(amount, "ERC20: transfer amount exceeds allowance"));
        return true;
    }

    /**
     * @dev Atomically increases the allowance granted to `spender` by the caller.
     *
     * This is an alternative to {approve} that can be used as a mitigation for
     * problems described in {IERC20-approve}.
     *
     * Emits an {Approval} event indicating the updated allowance.
     *
     * Requirements:
     *
     * - `spender` cannot be the zero address.
     */
    function increaseAllowance(address spender, uint256 addedValue) public returns (bool) {
        _approve(_msgSender(), spender, _allowances[_msgSender()][spender].add(addedValue));
        return true;
    }

    /**
     * @dev Atomically decreases the allowance granted to `spender` by the caller.
     *
     * This is an alternative to {approve} that can be used as a mitigation for
     * problems described in {IERC20-approve}.
     *
     * Emits an {Approval} event indicating the updated allowance.
     *
     * Requirements:
     *
     * - `spender` cannot be the zero address.
     * - `spender` must have allowance for the caller of at least
     * `subtractedValue`.
     */
    function decreaseAllowance(address spender, uint256 subtractedValue) public returns (bool) {
        _approve(_msgSender(), spender, _allowances[_msgSender()][spender].sub(subtractedValue, "ERC20: decreased allowance below zero"));
        return true;
    }

    /**
     * @dev Moves tokens `amount` from `sender` to `recipient`.
     *
     * This is internal function is equivalent to {transfer}, and can be used to
     * e.g. implement automatic token fees, slashing mechanisms, etc.
     *
     * Emits a {Transfer} event.
     *
     * Requirements:
     *
     * - `sender` cannot be the zero address.
     * - `recipient` cannot be the zero address.
     * - `sender` must have a balance of at least `amount`.
     */
    function _transfer(address sender, address recipient, uint256 amount) internal {
        require(sender != address(0), "ERC20: transfer from the zero address");
        require(recipient != address(0), "ERC20: transfer to the zero address");

        _balances[sender] = _balances[sender].sub(amount, "ERC20: transfer amount exceeds balance");
        _balances[recipient] = _balances[recipient].add(amount);
        emit Transfer(sender, recipient, amount);
    }

    /** @dev Creates `amount` tokens and assigns them to `account`, increasing
     * the total supply.
     *
     * Emits a {Transfer} event with `from` set to the zero address.
     *
     * Requirements
     *
     * - `to` cannot be the zero address.
     */
    function _mint(address account, uint256 amount) internal {
        require(account != address(0), "ERC20: mint to the zero address");

        _totalSupply = _totalSupply.add(amount);
        _balances[account] = _balances[account].add(amount);
        emit Transfer(address(0), account, amount);
    }

    /**
     * @dev Destroys `amount` tokens from `account`, reducing the
     * total supply.
     *
     * Emits a {Transfer} event with `to` set to the zero address.
     *
     * Requirements
     *
     * - `account` cannot be the zero address.
     * - `account` must have at least `amount` tokens.
     */
    function _burn(address account, uint256 amount) internal {
        require(account != address(0), "ERC20: burn from the zero address");

        _balances[account] = _balances[account].sub(amount, "ERC20: burn amount exceeds balance");
        _totalSupply = _totalSupply.sub(amount);
        emit Transfer(account, address(0), amount);
    }

    /**
     * @dev Sets `amount` as the allowance of `spender` over the `owner`s tokens.
     *
     * This is internal function is equivalent to `approve`, and can be used to
     * e.g. set automatic allowances for certain subsystems, etc.
     *
     * Emits an {Approval} event.
     *
     * Requirements:
     *
     * - `owner` cannot be the zero address.
     * - `spender` cannot be the zero address.
     */
    function _approve(address owner, address spender, uint256 amount) internal {
        require(owner != address(0), "ERC20: approve from the zero address");
        require(spender != address(0), "ERC20: approve to the zero address");

        _allowances[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }

    /**
     * @dev Destroys `amount` tokens from `account`.`amount` is then deducted
     * from the caller's allowance.
     *
     * See {_burn} and {_approve}.
     */
    function _burnFrom(address account, uint256 amount) internal {
        _burn(account, amount);
        _approve(account, _msgSender(), _allowances[account][_msgSender()].sub(amount, "ERC20: burn amount exceeds allowance"));
    }
}

// File: localhost/solidity/minted_erc20.sol

pragma solidity ^0.5.10;



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
// File: localhost/solidity/eth_merkle_bridge.sol

pragma solidity ^0.5.10;


contract EthMerkleBridge {
    // Trie root of the opposit side bridge contract. Mints and Unlocks require a merkle proof
    // of state inclusion in this last Root.
    bytes32 public _anchorRoot;
    // Height of the last block anchored
    uint public _anchorHeight;
    // _tAnchor is the anchoring periode of the bridge
    uint public _tAnchor;
    // _tFinal is the time after which the bridge operator consideres a block finalised
    // this value is only useful if the anchored chain doesn't have LIB
    // Since Aergo has LIB it is a simple indicator for wallets.
    uint public _tFinal;
    // address that controls anchoring and settings of the bridge
    address public _oracle;

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

    event newMintedERC20(string indexed origin, MintedERC20 indexed addr);
    event lockEvent(address indexed sender, IERC20 indexed tokenAddress, string indexed receiver, uint amount);
    event unlockEvent(address indexed sender, IERC20 indexed tokenAddress, address indexed receiver, uint amount);
    event mintEvent(address indexed sender, MintedERC20 indexed tokenAddress, address indexed receiver, uint amount);
    event burnEvent(address indexed sender, MintedERC20 indexed tokenAddress, string indexed receiver, uint amount);
    event anchorEvent(address indexed sender, bytes32 root, uint height);
    event newTAnchorEvent(address indexed sender, uint tAnchor);
    event newTFinalEvent(address indexed sender, uint tFinal);
    event newOracleEvent(address indexed sender, address newOracle);

    constructor(
        uint tAnchor,
        uint tFinal
    ) public {
        _tAnchor = tAnchor;
        _tFinal = tFinal;
        // the oracle is set to the sender who must transfer ownership to oracle contract
        // with oracleUpdate(), once deployed
        _oracle = msg.sender;
    }


    // Throws if called by any account other than the owner.
    modifier onlyOracle() {
        require(msg.sender == _oracle, "Only oracle can call");
        _;
    }

    // Change the current oracle contract
    // @param   newOracle - address of new oracle
    function oracleUpdate(
        address newOracle
    ) public onlyOracle {
        require(newOracle != address(0), "Don't burn the oracle");
        _oracle = newOracle;
        emit newOracleEvent(msg.sender, newOracle);
    }

    // Register new anchoring periode
    // @param   tAnchor - new anchoring periode
    function tAnchorUpdate(
        uint tAnchor
    ) public onlyOracle {
        _tAnchor = tAnchor;
        emit newTAnchorEvent(msg.sender, tAnchor);
    }

    // Register new finality of anchored chain
    // @param   tFinal - new finality of anchored chain
    function tFinalUpdate(
        uint tFinal
    ) public onlyOracle {
        _tFinal = tFinal;
        emit newTFinalEvent(msg.sender, tFinal);
    }

    // Register a new anchor
    // @param   root - Aergo storage root
    // @param   height - block height of root
    function newAnchor(
        bytes32 root,
        uint height
    ) public onlyOracle {
        require(height > _anchorHeight + _tAnchor, "Next anchor height not reached");
        _anchorRoot = root;
        _anchorHeight = height;
        emit anchorEvent(msg.sender, root, height);
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
        string memory addr = _mintedTokens[address(token)];
        require(bytes(addr).length == 0, "cannot lock token that was minted by bridge, must be burnt");
        // Add locked amount to total
        bytes memory accountRef = abi.encodePacked(receiver, token);
        _locks[accountRef] += amount;
        require(_locks[accountRef] >= amount, "total _locks overflow");
        // Pull token from owner to bridge contract (owner must set approval before calling lock)
        // using msg.sender, the owner must call lock, but we can make delegated transfers with sender
        // address as parameter.
        require(token.transferFrom(msg.sender, address(this), amount), "Failed to lock");
        emit lockEvent(msg.sender, token, receiver, amount);
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
        require(verifyDepositProof("_sv__burns-", accountRef, balance, mp, bitmap, leafHeight), "Failed to verify lock proof");
        uint unlockedSoFar = _unlocks[accountRef];
        uint amountToTransfer = balance - unlockedSoFar;
        require(amountToTransfer>0, "Burn tokens before unlocking");
        _unlocks[accountRef] = balance;
        require(token.transfer(receiver, amountToTransfer), "Failed to transfer unlock");
        emit unlockEvent(msg.sender, token, receiver, amountToTransfer);
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
        require(verifyDepositProof("_sv__locks-", accountRef, balance, mp, bitmap, leafHeight), "Failed to verify lock proof");
        uint mintedSoFar = _mints[accountRef];
        uint amountToTransfer = balance - mintedSoFar;
        require(amountToTransfer>0, "Lock tokens before minting");
        MintedERC20 mintAddress = _bridgeTokens[tokenOrigin];
        if (mintAddress == MintedERC20(0)) {
            // first time bridging this token
            mintAddress = new MintedERC20(tokenOrigin);
            _bridgeTokens[tokenOrigin] = mintAddress;
            _mintedTokens[address(mintAddress)] = tokenOrigin;
            emit newMintedERC20(tokenOrigin, mintAddress);
        }
        _mints[accountRef] = balance;
        require(mintAddress.mint(receiver, amountToTransfer), "Failed to mint");
        emit mintEvent(msg.sender, mintAddress, receiver, amountToTransfer);
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
        require(_burns[accountRef] >= amount, "total _burns overflow");
        // Burn token
        require(mintAddress.burn(msg.sender, amount), "Failed to burn");
        emit burnEvent(msg.sender, mintAddress, receiver, amount);
        return true;
    }

    // Aergo State Trie Merkle proof verification
    // @param   mapName - name of Lua map variable storing locked/burnt balances
    // @param   accountRef - key in mapName to record an account's token balance
    // @param   balance - balance recorded in accountRef of mapName
    // @param   mp - merkle proof of inclusion of accountRef, balance in _anchorRoot
    // @param   bitmap - bitmap of non default nodes in the merkle proof
    // @param   leafHeight - height of leaf containing the value in the state SMT
    function verifyDepositProof(
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

    // Lua contracts don't store real bytes of uint so converting to string in necessary
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