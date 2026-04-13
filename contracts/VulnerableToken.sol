// SPDX-License-Identifier: MIT
pragma solidity ^0.7.0;

// WARNING: This contract is intentionally vulnerable for testing purposes.
// Do NOT deploy this in production.

contract VulnerableToken {
    mapping(address => uint256) public balances;
    mapping(address => mapping(address => uint256)) public allowances;
    address public owner;
    uint256 public totalSupply;

    constructor() {
        owner = msg.sender;
        totalSupply = 1000000 * 10 ** 18;
        balances[msg.sender] = totalSupply;
    }

    // Vulnerability 1: Reentrancy
    // Balance is updated AFTER the external call, allowing reentrancy attacks
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        balances[msg.sender] -= amount;  // state update too late
    }

    // Vulnerability 2: Missing access control
    // Anyone can call mint, not just the owner
    function mint(address to, uint256 amount) public {
        totalSupply += amount;
        balances[to] += amount;
    }

    // Vulnerability 3: Integer overflow (Solidity 0.7 has no built-in overflow check)
    function transfer(address to, uint256 amount) public returns (bool) {
        balances[msg.sender] -= amount;
        balances[to] += amount;
        return true;
    }

    // Vulnerability 4: Unchecked return value
    function unsafeTransferETH(address payable to, uint256 amount) public {
        to.send(amount);  // return value not checked
    }

    // Vulnerability 5: Timestamp dependence
    function claimBonus() public {
        require(block.timestamp % 2 == 0, "Try again");
        balances[msg.sender] += 100 * 10 ** 18;
    }

    receive() external payable {}
}
