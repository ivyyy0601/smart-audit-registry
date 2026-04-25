// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

/**
 * @title SafeToken
 * @notice A secure ERC20 token with safe withdrawal, minting, and bonus claiming.
 * Designed to be the "safe" counterpart to VulnerableToken for audit comparison.
 *
 * Security features:
 * - Solidity ^0.8.20: built-in overflow/underflow protection
 * - ReentrancyGuard: prevents reentrancy on withdraw
 * - Ownable: only owner can mint
 * - Checks-Effects-Interactions: state updated before external call
 * - Unchecked return values: handled via call() with require(success)
 * - Timestamp: used only for non-critical cooldown, not randomness
 */
contract SafeToken is ERC20, Ownable, ReentrancyGuard, Pausable {

    // ETH balances tracked separately from token balances
    mapping(address => uint256) public ethBalances;

    // Cooldown: one bonus claim per 24 hours per address
    mapping(address => uint256) public lastClaimed;
    uint256 public constant CLAIM_COOLDOWN = 24 hours;
    uint256 public constant BONUS_AMOUNT   = 100 * 10 ** 18;

    event Deposited(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event BonusClaimed(address indexed user, uint256 amount);

    constructor() ERC20("SafeToken", "SAFE") Ownable(msg.sender) {
        // Mint initial supply to owner
        _mint(msg.sender, 1_000_000 * 10 ** decimals());
    }

    // ── Deposit ETH ───────────────────────────────────────────────────────────

    receive() external payable {
        ethBalances[msg.sender] += msg.value;
        emit Deposited(msg.sender, msg.value);
    }

    // ── Safe Withdraw (fixed reentrancy) ──────────────────────────────────────

    /**
     * @notice Withdraw ETH — state updated BEFORE external call (CEI pattern).
     * nonReentrant guard provides an additional layer of protection.
     */
    function withdraw(uint256 amount) external nonReentrant whenNotPaused {
        require(amount > 0, "Amount must be > 0");
        require(ethBalances[msg.sender] >= amount, "Insufficient balance");

        // Effects: update state before interaction
        ethBalances[msg.sender] -= amount;

        // Interactions: external call last
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "ETH transfer failed");

        emit Withdrawn(msg.sender, amount);
    }

    // ── Mint (access controlled) ──────────────────────────────────────────────

    /**
     * @notice Only owner can mint — prevents unauthorized token inflation.
     */
    function mint(address to, uint256 amount) external onlyOwner {
        require(to != address(0), "Cannot mint to zero address");
        _mint(to, amount);
    }

    // ── Safe ETH Transfer (return value checked) ──────────────────────────────

    /**
     * @notice Transfer ETH with explicit success check.
     * Only owner can call — prevents unauthorized fund drain.
     */
    function safeTransferETH(address payable to, uint256 amount)
        external
        onlyOwner
        nonReentrant
    {
        require(to != address(0), "Cannot send to zero address");
        require(address(this).balance >= amount, "Insufficient contract balance");

        (bool success, ) = to.call{value: amount}("");
        require(success, "ETH transfer failed");
    }

    // ── Claim Bonus (no timestamp manipulation risk) ──────────────────────────

    /**
     * @notice Claim bonus tokens once every 24 hours.
     * Timestamp used for cooldown only — not for randomness or exact precision.
     * 15-second miner manipulation window has no meaningful impact on a 24h cooldown.
     */
    function claimBonus() external whenNotPaused {
        require(
            block.timestamp >= lastClaimed[msg.sender] + CLAIM_COOLDOWN,
            "Cooldown not elapsed"
        );

        lastClaimed[msg.sender] = block.timestamp;
        _mint(msg.sender, BONUS_AMOUNT);

        emit BonusClaimed(msg.sender, BONUS_AMOUNT);
    }

    // ── Admin ─────────────────────────────────────────────────────────────────

    function pause()   external onlyOwner { _pause(); }
    function unpause() external onlyOwner { _unpause(); }
}
