------------------------------------------------------------------------------
-- Merkle bridge contract
------------------------------------------------------------------------------

-- Internal type check function
-- @type internal
-- @param x variable to check
-- @param t (string) expected type
local function _typecheck(x, t)
  if (x and t == 'address') then
    assert(type(x) == 'string', "address must be string type")
    -- check address length
    assert(52 == #x, string.format("invalid address length: %s (%s)", x, #x))
    -- check character
    local invalidChar = string.match(x, '[^123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]')
    assert(nil == invalidChar, string.format("invalid address format: %s contains invalid char %s", x, invalidChar or 'nil'))
  elseif (x and t == 'ethaddress') then
    assert(type(x) == 'string', "eth address must be string type")
    -- check address length
    assert(40 == #x, string.format("invalid eth address length: %s (%s)", x, #x))
    -- check character
    local invalidChar = string.match(x, '[^0123456789abcdef]')
    assert(nil == invalidChar, string.format("invalid eth address format: %s contains invalid char %s", x, invalidChar or 'nil'))
  elseif (x and t == 'ubig') then
    -- check unsigned bignum
    assert(bignum.isbignum(x), string.format("invalid type: %s != %s", type(x), t))
    assert(x >= bignum.number(0), string.format("%s must be positive number", bignum.tostring(x)))
  else
    -- check default lua types
    assert(type(x) == t, string.format("invalid type: %s != %s", type(x), t or 'nil'))
  end
end

-- Stores latest finalised bridge contract state root of ethereum blockchain at regular intervals.
-- Enables Users to verify state information of the connected chain 
-- using merkle proofs for the finalised state root.
state.var {
    -- Trie root of the opposit side bridge contract. _mints and _unlocks require a merkle proof
    -- of state inclusion in this last Root.
    -- (hex string without 0x prefix)
    _anchorRoot = state.value(),
    -- Height of the last block anchored
    -- (uint)
    _anchorHeight = state.value(),

    -- _tAnchor is the anchoring periode of the bridge
    -- (uint)
    _tAnchor = state.value(),
    -- _tFinal is the time after which the bridge operator consideres a block finalised
    -- this value is only useful if the anchored chain doesn't have LIB
    -- (uint)
    _tFinal = state.value(),
    -- _aergoErc20Bytes is the Aergo token contract address bytes on Ethereum
    -- (Ethereum address)
    _aergoErc20Bytes = state.value(),
    -- unfreezeFee gives a fee to the tx sender to enable free unfreezing of aergo on mainnet
    _unfreezeFee = state.value(),
    -- oracle that controls this bridge.
    _oracle = state.value(),

    -- Registers locked balances per account reference: user provides merkle proof of locked balance
    -- (account ref string) -> (string uint)
    _locks = state.map(),
    -- Registers unlocked balances per account reference: prevents unlocking more than was burnt
    -- (account ref string) -> (string uint)
    _unlocks = state.map(),
    -- Registers burnt balances per account reference : user provides merkle proof of burnt balance
    -- (account ref string) -> (string uint)
    _burns = state.map(),
    -- Registers minted balances per account reference : prevents minting more than what was locked
    -- (account ref string) -> (string uint)
    _mints = state.map(),
    -- Registers unfreezed balances per account reference : prevents unfreezing more than was locked
    -- (account ref string) -> (string uint)
    _unfreezes = state.map(),
    -- _bridgeTokens keeps track of tokens that were received through the bridge
    -- (Ethereum address) -> (Aergo address)
    _bridgeTokens = state.map(),
    -- _mintedTokens is the same as BridgeTokens but keys and values are swapped
    -- _mintedTokens is used for preventing a minted token from being locked instead of burnt.
    -- (Aergo address) -> (Ethereum address)
    _mintedTokens = state.map(),
}


--------------------- Utility Functions -------------------------

local function _onlyOracle()
    assert(system.getSender() == _oracle:get(), string.format("Only oracle can call, expected: %s, got: %s", _oracle:get(), system.getSender()))
end


-- Convert hex string to lua bytes
-- @type    internal
-- @param   hexString (hex string) hex string without 0x
-- @return  (string bytes) bytes of hex string
local function _abiEncode(hexString)
    return (hexString:gsub('..', function (cc)
        return string.char(tonumber(cc, 16))
    end))
end

-- Ethereum Patricia State Trie Merkle proof verification
-- @type    internal
-- @param   mapKey (string bytes) key in solidity map
-- @param   mapPosition (uint) position of mapping state var in solidity contract
-- @param   value (string bytes) value of mapKey in solidity map at mapPosition
-- @param   merkleProof ([]0x hex string) merkle proof of inclusion of mapKey, value in _anchorRoot
-- @return  (bool) merkle proof of inclusion is valid
local function _verifyDepositProof(mapKey, mapPosition, value, merkleProof)
    -- map key is always >= 32 bytes so no padding needed
    paddedPosition = "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0" .. string.char(mapPosition)
    key = crypto.keccak256(mapKey..paddedPosition)
    return crypto.verifyProof(key, value, "0x" .. _anchorRoot:get(), unpack(merkleProof))
end

-- deploy new contract
-- @type    internal
-- @param   tokenOrigin (ethaddress) Ethereum address without 0x of token locked used as pegged token name
local function _deployMinteableToken(tokenOrigin)
    addr, success = contract.deploy(mintedTokenCode, tokenOrigin)
    assert(success, "failed to create peg token contract")
    return addr
end

-- lock tokens in the bridge contract
-- @type    internal
-- @param   tokenAddress (address) Aergo address of token locked
-- @param   amount (ubig) amount of tokens to send
-- @param   receiver (ethaddress) Ethereum address without 0x of receiver accross the bridge
-- @event   lock(receiver, amount, tokenAddress)
local function _lock(tokenAddress, amount, receiver)
    _typecheck(receiver, 'ethaddress')
    _typecheck(amount, 'ubig')
    assert(_mintedTokens[tokenAddress] == nil, "this token was minted by the bridge so it should be burnt to transfer back to origin, not locked")
    assert(amount > bignum.number(0), "amount must be positive")

    -- Add locked amount to total
    local accountRef =  _abiEncode(receiver) .. tokenAddress
    local old = _locks[accountRef]
    local lockedBalance
    if old == nil then
        lockedBalance = amount
    else
        lockedBalance = bignum.number(old) + amount
        -- bignum overflow raises error
    end
    _locks[accountRef] = bignum.tostring(lockedBalance)
    contract.event("lock", receiver, amount, tokenAddress)
end

-- Create a new bridge contract
-- @type    __init__
-- @param   aergoErc20 (ethaddress) Ethereum address without 0x of aergoErc20
-- @param   tAnchor (uint) anchoring periode
-- @param   tFinal (uint) finality of anchored chain
-- @param   unfreeze_fee (ubig) fee taken when a thirs party unfreezes
function constructor(aergoErc20, tAnchor, tFinal, unfreeze_fee)
    _typecheck(aergoErc20, 'ethaddress')
    _typecheck(unfreeze_fee, 'ubig')
    _aergoErc20Bytes:set(_abiEncode(aergoErc20))
    _tAnchor:set(tAnchor)
    _tFinal:set(tFinal)
    _anchorRoot:set("constructor")
    _anchorHeight:set(0)
    _unfreezeFee:set(bignum.number(1000))
    -- the oracle is set to the sender who must transfer ownership to oracle contract
    -- with oracleUpdate(), once deployed
    _oracle:set(system.getSender())
end

--------------------- Bridge Operator Functions -------------------------

function default()
    contract.event("initializeVault", system.getSender(), system.getAmount())
    -- needed to send the vault funds when starting the bridge
    -- consider disabling after 1st transfer so users don't send 
    -- funds by mistake
end

-- Replace the oracle with another one
-- @type    call
-- @param   newOracle (address) Aergo address of the new oracle
-- @event   oracleUpdate(proposer, newOracle)
function oracleUpdate(newOracle)
    _onlyOracle()
    _oracle:set(newOracle)
    contract.event("oracleUpdate", system.getSender(), newOracle)
end

-- Register a new anchor
-- @type    call
-- @param   root (ethaddress) Ethereum storage root
-- @param   height (uint) block height of root
-- @event   newAnchor(proposer, height, root)
function newAnchor(root, height)
    _onlyOracle()
    -- check Height to prevent spamming and leave minimum time for users to make transfers.
    assert(height > _anchorHeight:get() + _tAnchor:get(), "Next anchor height not reached")
    _anchorRoot:set(root)
    _anchorHeight:set(height)
    contract.event("newAnchor", system.getSender(), height, root)
end


-- Register new anchoring periode
-- @type    call
-- @param   tAnchor (uint) new anchoring periode
-- @event   tAnchorUpdate(proposer, tAnchor)
function tAnchorUpdate(tAnchor)
    _onlyOracle()
    _tAnchor:set(tAnchor)
    contract.event("tAnchorUpdate", system.getSender(), tAnchor)
end

-- Register new finality of anchored chain
-- @type    call
-- @param   tFinal (uint) new finality of anchored chain
-- @event   tFinalUpdate(proposer, tFinal)
function tFinalUpdate(tFinal)
    _onlyOracle()
    _tFinal:set(tFinal)
    contract.event("tFinalUpdate", system.getSender(), tFinal)
end

-- Register new unfreezing fee for delegated unfreeze service
-- @type    call
-- @param   fee (ubig) new unfreeze fee
-- @event   unfreezeFeeUpdate(proposer, fee)
function unfreezeFeeUpdate(fee)
    _onlyOracle()
    _unfreezeFee:set(fee)
    contract.event("unfreezeFeeUpdate", system.getSender(), fee)
end

--------------------- User Transfer Functions -------------------------

-- The ARC1 smart contract calls this function on the recipient after a 'transfer'
-- @type    call
-- @param   operator    (address) the address which called token 'transfer' function
-- @param   from        (address) the sender's address
-- @param   value       (ubig) an amount of token to send
-- @param   receiver    (ethaddress) Ethereum address without 0x of receiver accross the bridge
function tokensReceived(operator, from, value, receiver)
    return _lock(system.getSender(), value, receiver)
end


-- mint a token locked on Ethereum
-- AergoERC20 is locked on ethereum like any other tokens, but it is not minted, it is unfreezed.
-- anybody can mint, the receiver is the account who's locked balance is recorded
-- @type    call
-- @param   receiver (address) Aergo address of receiver
-- @param   balance (ubig) total balance of tokens locked on Ethereum
-- @param   tokenOrigin (ethaddress) Ethereum address without 0x of ERC20 token locked
-- @param   merkleProof ([]0x hex string) merkle proof of inclusion of locked balance on Ethereum
-- @return  (address, uint) pegged token Aergo address, minted amount
-- @event   mint(minter, receiver, amount, tokenOrigin)
function mint(receiver, balance, tokenOrigin, merkleProof)
    _typecheck(receiver, 'address')
    _typecheck(balance, 'ubig')
    _typecheck(tokenOrigin, 'ethaddress')
    assert(balance > bignum.number(0), "minteable balance must be positive")
    tokenOriginBytes = _abiEncode(tokenOrigin)
    assert(tokenOriginBytes ~= _aergoErc20Bytes:get(), "Aergo cannot be minted, must be unfreezed")

    -- Verify merkle proof of locked balance
    local accountRef = receiver .. tokenOriginBytes
    -- Locks is the 6th variable of eth_merkle_bridge.col so mapPosition = 5
    if not _verifyDepositProof(accountRef, 5, bignum.tobyte(balance), merkleProof) then
        error("failed to verify deposit balance merkle proof")
    end
    -- Calculate amount to mint
    local amountToTransfer
    mintedSoFar = _mints[accountRef]
    if mintedSoFar == nil then
        amountToTransfer = balance
    else
        amountToTransfer  = balance - bignum.number(mintedSoFar)
    end
    assert(amountToTransfer > bignum.number(0), "make a deposit before minting")
    -- Deploy or get the minted token
    local mintAddress
    if _bridgeTokens[tokenOrigin] == nil then
        -- Deploy new minteable token controlled by bridge
        mintAddress = _deployMinteableToken(tokenOrigin)
        _bridgeTokens[tokenOrigin] = mintAddress
        _mintedTokens[mintAddress] = tokenOrigin
    else
        mintAddress = _bridgeTokens[tokenOrigin]
    end
    -- Record total amount minted
    _mints[accountRef] = bignum.tostring(balance)
    -- Mint tokens
    contract.call(mintAddress, "mint", receiver, amountToTransfer)
    contract.event("mint", system.getSender(), receiver, amountToTransfer, tokenOrigin)
    return mintAddress, amountToTransfer
end

-- burn a pegged token
-- @type    call
-- @param   receiver (ethaddress) Ethereum address without 0x of receiver
-- @param   amount (ubig) number of tokens to burn
-- @param   mintAddress (address) Aergo address of pegged token to burn
-- @return  (ethaddress) Ethereum address without 0x of origin token
-- @event   brun(owner, receiver, amount, mintAddress)
function burn(receiver, amount, mintAddress)
    _typecheck(receiver, 'ethaddress')
    _typecheck(amount, 'ubig')
    assert(amount > bignum.number(0), "amount must be positive")
    local originAddress = _mintedTokens[mintAddress]
    assert(originAddress ~= nil, "cannot burn token : must have been minted by bridge")
    -- Add burnt amount to total
    local accountRef = _abiEncode(receiver .. originAddress)
    local old = _burns[accountRef]
    local burntBalance
    if old == nil then
        burntBalance = amount
    else
        burntBalance = bignum.number(old) + amount
        -- bignum overflow raises error
    end
    _burns[accountRef] = bignum.tostring(burntBalance)
    -- Burn token
    contract.call(mintAddress, "burn", system.getSender(), amount)
    contract.event("burn", system.getSender(), receiver, amount, mintAddress)
    return originAddress
end

-- unlock tokens
-- anybody can unlock, the receiver is the account who's burnt balance is recorded
-- @type    call
-- @param   receiver (address) Aergo address of receiver
-- @param   balance (ubig) total balance of tokens burnt on Ethereum
-- @param   tokenAddress (address) Aergo address of token to unlock
-- @param   merkleProof ([]0x hex string) merkle proof of inclusion of burnt balance on Ethereum
-- @return  (uint) unlocked amount
-- @event   unlock(unlocker, receiver, amount, tokenAddress)
function unlock(receiver, balance, tokenAddress, merkleProof)
    _typecheck(receiver, 'address')
    _typecheck(tokenAddress, 'address')
    _typecheck(balance, 'ubig')
    assert(balance > bignum.number(0), "unlockeable balance must be positive")

    -- Verify merkle proof of burnt balance
    local accountRef = receiver .. tokenAddress
    -- Burns is the 8th variable of eth_merkle_bridge.col so mapPosition = 7
    if not _verifyDepositProof(accountRef, 7, bignum.tobyte(balance), merkleProof) then
        error("failed to verify burnt balance merkle proof")
    end
    -- Calculate amount to unlock
    local unlockedSoFar = _unlocks[accountRef]
    local amountToTransfer
    if unlockedSoFar == nil then
        amountToTransfer = balance
    else
        amountToTransfer = balance - bignum.number(unlockedSoFar)
    end
    assert(amountToTransfer > bignum.number(0), "burn minted tokens before unlocking")
    -- Record total amount unlocked so far
    _unlocks[accountRef] = bignum.tostring(balance)
    -- Unlock tokens
    contract.call(tokenAddress, "transfer", receiver, amountToTransfer)
    contract.event("unlock", system.getSender(), receiver, amountToTransfer, tokenAddress)
    return amountToTransfer
end


-- freeze mainnet aergo
-- @type    call
-- @param   receiver (ethaddress) Ethereum address without 0x of receiver
-- @param   amount (ubig) number of tokens to freeze
-- @event   freeze(owner, receiver, amount)
function freeze(receiver, amount)
    _typecheck(receiver, 'ethaddress')
    _typecheck(amount, 'ubig')
    -- passing amount is not necessary but system.getAmount() would have to be converted to bignum anyway.
    assert(amount > bignum.number(0), "amount must be positive")
    assert(system.getAmount() == bignum.tostring(amount), "for safety and clarity, amount must match the amount sent in the tx")

    -- Add freezed amount to total
    local accountRef = _abiEncode(receiver) .. _aergoErc20Bytes:get()
    local old = _burns[accountRef]
    local freezedBalance
    if old == nil then
        freezedBalance = amount
    else
        freezedBalance = bignum.number(old) + amount
    end
    _burns[accountRef] = bignum.tostring(freezedBalance)
    contract.event("freeze", system.getSender(), receiver, amount)
end


-- unfreeze mainnet aergo
-- anybody can unfreeze, the receiver is the account who's burnt balance is recorded
-- @type    call
-- @param   receiver (address) Aergo address of receiver
-- @param   balance (ubig) total balance of tokens locked on Ethereum
-- @param   merkleProof ([]0x hex string) merkle proof of inclusion of locked balance on Ethereum
-- @return  (uint) unfreezed amount
-- @event   unfreeze(unfreezer, receiver, amount)
function unfreeze(receiver, balance, merkleProof)
    _typecheck(receiver, 'address')
    _typecheck(balance, 'ubig')
    assert(balance > bignum.number(0), "unlockeable balance must be positive")

    -- Verify merkle proof of burnt balance
    local accountRef = receiver .. _aergoErc20Bytes:get()
    -- Locks is the 6th variable of eth_merkle_bridge.col so mapPosition = 5
    if not _verifyDepositProof(accountRef, 5, bignum.tobyte(balance), merkleProof) then
        error("failed to verify locked balance merkle proof")
    end
    -- Calculate amount to unfreeze
    local unfreezedSoFar = _unfreezes[accountRef]
    local amountToTransfer
    if unfreezedSoFar == nil then
        amountToTransfer = balance
    else
        amountToTransfer = balance - bignum.number(unfreezedSoFar)
    end
    assert(amountToTransfer > bignum.number(0), "lock AergoERC20 on ethereum before unfreezing")
    -- Record total amount unlocked so far
    _unfreezes[accountRef] = bignum.tostring(balance)
    -- Unfreeze Aer
    if system.getSender() == receiver then
        contract.send(receiver, amountToTransfer)
    else
        -- NOTE: the minting service should check that amount to transfer will cover the fee, to not mint for nothing
        assert(amountToTransfer > _unfreezeFee:get(), "amount to transfer doesnt cover the fee")
        contract.send(receiver, amountToTransfer - _unfreezeFee:get())
        contract.send(system.getSender(), _unfreezeFee:get())
    end
    contract.event("unfreeze", system.getSender(), receiver, amountToTransfer)
    return amountToTransfer
end

mintedTokenCode = [[
------------------------------------------------------------------------------
-- Aergo Standard Token Interface (Proposal) - 20190731
------------------------------------------------------------------------------

-- A internal type check function
-- @type internal
-- @param x variable to check
-- @param t (string) expected type
local function _typecheck(x, t)
  if (x and t == 'address') then
    assert(type(x) == 'string', "address must be string type")
    -- check address length
    assert(52 == #x, string.format("invalid address length: %s (%s)", x, #x))
    -- check character
    local invalidChar = string.match(x, '[^123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]')
    assert(nil == invalidChar, string.format("invalid address format: %s contains invalid char %s", x, invalidChar or 'nil'))
  elseif (x and t == 'ubig') then
    -- check unsigned bignum
    assert(bignum.isbignum(x), string.format("invalid type: %s != %s", type(x), t))
    assert(x >= bignum.number(0), string.format("%s must be positive number", bignum.tostring(x)))
  else
    -- check default lua types
    assert(type(x) == t, string.format("invalid type: %s != %s", type(x), t or 'nil'))
  end
end

address0 = '1111111111111111111111111111111111111111111111111111'

-- The bridge token is a mintable and burnable token controlled by
-- the bridge contract. It represents tokens pegged on the other side of the 
-- bridge with a 1:1 ratio.
-- This contract is depoyed by the merkle bridge when a new type of token 
-- is transfered
state.var {
    _balances = state.map(), -- address -> unsigned_bignum
    _operators = state.map(), -- address/address -> bool

    _totalSupply = state.value(),
    _name = state.value(),
    _symbol = state.value(),
    _decimals = state.value(),

    _master = state.value(),
}

local function _callTokensReceived(from, to, value, ...)
  if to ~= address0 and system.isContract(to) then
    contract.call(to, "tokensReceived", system.getSender(), from, value, ...)
  end
end

local function _transfer(from, to, value, ...)
  _typecheck(from, 'address')
  _typecheck(to, 'address')
  _typecheck(value, 'ubig')

  assert(_balances[from] and _balances[from] >= value, "not enough balance")

  _balances[from] = _balances[from] - value
  _balances[to] = (_balances[to] or bignum.number(0)) + value

  _callTokensReceived(from, to, value, ...)

  contract.event("transfer", from, to, value)
end

local function _mint(to, value, ...)
  _typecheck(to, 'address')
  _typecheck(value, 'ubig')

  _totalSupply:set((_totalSupply:get() or bignum.number(0)) + value)
  _balances[to] = (_balances[to] or bignum.number(0)) + value

  _callTokensReceived(address0, to, value, ...)

  contract.event("transfer", address0, to, value)
end

local function _burn(from, value)
  _typecheck(from, 'address')
  _typecheck(value, 'ubig')

  assert(_balances[from] and _balances[from] >= value, "not enough balance")

  _totalSupply:set(_totalSupply:get() - value)
  _balances[from] = _balances[from] - value

  contract.event("transfer", from, address0, value)
end

-- call this at constructor
local function _init(name, symbol, decimals)
  _typecheck(name, 'string')
  _typecheck(symbol, 'string')
  _typecheck(decimals, 'number')
  assert(decimals > 0)

  _name:set(name)
  _symbol:set(symbol)
  _decimals:set(decimals)
end

------------  Main Functions ------------

-- Get a total token supply.
-- @type    query
-- @return  (ubig) total supply of this token
function totalSupply()
  return _totalSupply:get()
end

-- Get a token name
-- @type    query
-- @return  (string) name of this token
function name()
  return _name:get()
end

-- Get a token symbol
-- @type    query
-- @return  (string) symbol of this token
function symbol()
  return _symbol:get()
end

-- Get a token decimals
-- @type    query
-- @return  (number) decimals of this token
function decimals()
  return _decimals:get()
end

-- Get a balance of an owner.
-- @type    query
-- @param   owner  (address) a target address
-- @return  (ubig) balance of owner
function balanceOf(owner)
  return _balances[owner] or bignum.number(0)
end

-- Transfer sender's token to target 'to'
-- @type    call
-- @param   to      (address) a target address
-- @param   value   (ubig) an amount of token to send
-- @param   ...     addtional data, MUST be sent unaltered in call to 'tokensReceived' on 'to'
-- @event   transfer(from, to, value)
function transfer(to, value, ...)
  _transfer(system.getSender(), to, value, ...)
end

-- Get allowance from owner to spender
-- @type    query
-- @param   owner       (address) owner's address
-- @param   operator    (address) allowed address
-- @return  (bool) true/false
function isApprovedForAll(owner, operator)
  return (owner == operator) or (_operators[owner.."/".. operator] == true)
end

-- Allow operator to use all sender's token
-- @type    call
-- @param   operator  (address) a operator's address
-- @param   approved  (boolean) true/false
-- @event   approve(owner, operator, approved)
function setApprovalForAll(operator, approved)
  _typecheck(operator, 'address')
  _typecheck(approved, 'boolean')
  assert(system.getSender() ~= operator, "cannot set approve self as operator")

  _operators[system.getSender().."/".. operator] = approved

  contract.event("approve", system.getSender(), operator, approved)
end

-- Transfer 'from's token to target 'to'.
-- Tx sender have to be approved to spend from 'from'
-- @type    call
-- @param   from    (address) a sender's address
-- @param   to      (address) a receiver's address
-- @param   value   (ubig) an amount of token to send
-- @param   ...     addtional data, MUST be sent unaltered in call to 'tokensReceived' on 'to'
-- @event   transfer(from, to, value)
function transferFrom(from, to, value, ...)
  assert(isApprovedForAll(from, system.getSender()), "caller is not approved for holder")

  _transfer(from, to, value, ...)
end

-------------- Merkle Bridge functions -----------------
--------------------------------------------------------

-- Mint tokens to 'to'
-- @type        call
-- @param to    a target address
-- @param value string amount of token to mint
-- @return      success
function mint(to, value)
    assert(system.getSender() == _master:get(), "Only bridge contract can mint")
    _mint(to, value)
end

-- burn the tokens of 'from'
-- @type        call
-- @param from  a target address
-- @param value an amount of token to send
-- @return      success
function burn(from, value)
    assert(system.getSender() == _master:get(), "Only bridge contract can burn")
    _burn(from, value)
end

--------------- Custom constructor ---------------------
--------------------------------------------------------
function constructor(originAddress) 
    _init(originAddress, 'PEG', 18)
    _totalSupply:set(bignum.number(0))
    _master:set(system.getSender())
    return true
end
--------------------------------------------------------

abi.register(transfer, transferFrom, setApprovalForAll, mint, burn)
abi.register_view(name, symbol, decimals, totalSupply, balanceOf, isApprovedForAll)
]]

abi.register(oracleUpdate, newAnchor, tAnchorUpdate, tFinalUpdate, unfreezeFeeUpdate, tokensReceived, unlock, mint, burn, unfreeze)
abi.payable(freeze, default)
