// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract AuditRegistry {

    struct AuditRecord {
        address submitter;      // wallet address of the auditor
        uint256 riskScore;      // risk score from 0 to 100
        string  summary;        // short audit summary stored on-chain
        string  reportHash;     // IPFS CID of the full audit report
        uint256 timestamp;      // block timestamp when record was submitted
        bool    exists;
    }

    // contractId (keccak256 hash) => list of audit records (supports multiple audits)
    mapping(bytes32 => AuditRecord[]) private records;

    event AuditSubmitted(
        bytes32 indexed contractId,
        address indexed submitter,
        uint256 riskScore,
        string  reportHash,
        uint256 timestamp
    );

    // Submit a new audit record.
    // contractId: keccak256 hash of the contract address or file identifier
    function submitAudit(
        bytes32 contractId,
        uint256 riskScore,
        string calldata summary,
        string calldata reportHash
    ) external {
        require(riskScore <= 100, "Risk score must be 0-100");
        require(bytes(reportHash).length > 0, "Report hash required");

        records[contractId].push(AuditRecord({
            submitter:  msg.sender,
            riskScore:  riskScore,
            summary:    summary,
            reportHash: reportHash,
            timestamp:  block.timestamp,
            exists:     true
        }));

        emit AuditSubmitted(contractId, msg.sender, riskScore, reportHash, block.timestamp);
    }

    // Get the most recent audit record for a contract
    function getLatestAudit(bytes32 contractId)
        external view
        returns (
            address submitter,
            uint256 riskScore,
            string memory summary,
            string memory reportHash,
            uint256 timestamp
        )
    {
        AuditRecord[] storage list = records[contractId];
        require(list.length > 0, "No audit record found");
        AuditRecord storage r = list[list.length - 1];
        return (r.submitter, r.riskScore, r.summary, r.reportHash, r.timestamp);
    }

    // Get the total number of audits for a contract
    function getAuditCount(bytes32 contractId) external view returns (uint256) {
        return records[contractId].length;
    }

    // Get a specific audit record by index (0 = first audit)
    function getAuditAt(bytes32 contractId, uint256 index)
        external view
        returns (
            address submitter,
            uint256 riskScore,
            string memory summary,
            string memory reportHash,
            uint256 timestamp
        )
    {
        AuditRecord[] storage list = records[contractId];
        require(index < list.length, "Index out of bounds");
        AuditRecord storage r = list[index];
        return (r.submitter, r.riskScore, r.summary, r.reportHash, r.timestamp);
    }

    // Verify whether a given report hash matches any on-chain record
    function verifyReport(bytes32 contractId, string calldata reportHash)
        external view
        returns (bool matched, uint256 matchedIndex)
    {
        AuditRecord[] storage list = records[contractId];
        for (uint256 i = 0; i < list.length; i++) {
            if (keccak256(bytes(list[i].reportHash)) == keccak256(bytes(reportHash))) {
                return (true, i);
            }
        }
        return (false, 0);
    }

    // Helper: convert a contract address to a contractId (bytes32)
    function addressToId(address contractAddr) external pure returns (bytes32) {
        return keccak256(abi.encodePacked(contractAddr));
    }

    // Helper: convert any string identifier (e.g. filename) to a contractId (bytes32)
    function stringToId(string calldata identifier) external pure returns (bytes32) {
        return keccak256(abi.encodePacked(identifier));
    }
}
