"""
Client for interacting with the AuditRegistry contract on Sepolia.
"""
import os
from web3 import Web3

# ABI for AuditRegistry.sol — copy the full ABI from Remix after deployment if needed
ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "contractId", "type": "bytes32"},
            {"internalType": "uint256", "name": "riskScore",  "type": "uint256"},
            {"internalType": "string",  "name": "summary",    "type": "string"},
            {"internalType": "string",  "name": "reportHash", "type": "string"}
        ],
        "name": "submitAudit",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "contractId", "type": "bytes32"}],
        "name": "getLatestAudit",
        "outputs": [
            {"internalType": "address", "name": "submitter",  "type": "address"},
            {"internalType": "uint256", "name": "riskScore",  "type": "uint256"},
            {"internalType": "string",  "name": "summary",    "type": "string"},
            {"internalType": "string",  "name": "reportHash", "type": "string"},
            {"internalType": "uint256", "name": "timestamp",  "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "contractId", "type": "bytes32"}],
        "name": "getAuditCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "contractId", "type": "bytes32"},
            {"internalType": "uint256", "name": "index",      "type": "uint256"}
        ],
        "name": "getAuditAt",
        "outputs": [
            {"internalType": "address", "name": "submitter",  "type": "address"},
            {"internalType": "uint256", "name": "riskScore",  "type": "uint256"},
            {"internalType": "string",  "name": "summary",    "type": "string"},
            {"internalType": "string",  "name": "reportHash", "type": "string"},
            {"internalType": "uint256", "name": "timestamp",  "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "contractId", "type": "bytes32"},
            {"internalType": "string",  "name": "reportHash", "type": "string"}
        ],
        "name": "verifyReport",
        "outputs": [
            {"internalType": "bool",    "name": "matched",      "type": "bool"},
            {"internalType": "uint256", "name": "matchedIndex", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "string", "name": "identifier", "type": "string"}],
        "name": "stringToId",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "pure",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "contractAddr", "type": "address"}],
        "name": "addressToId",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "pure",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "internalType": "bytes32", "name": "contractId", "type": "bytes32"},
            {"indexed": True,  "internalType": "address", "name": "submitter",  "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "riskScore",  "type": "uint256"},
            {"indexed": False, "internalType": "string",  "name": "reportHash", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp",  "type": "uint256"}
        ],
        "name": "AuditSubmitted",
        "type": "event"
    }
]


class AuditRegistryClient:
    def __init__(self):
        rpc_url          = os.getenv("SEPOLIA_RPC_URL")
        contract_address = os.getenv("AUDIT_REGISTRY_ADDRESS")
        private_key      = os.getenv("DEPLOYER_PRIVATE_KEY")

        if not rpc_url or not contract_address or not private_key:
            raise ValueError("SEPOLIA_RPC_URL, AUDIT_REGISTRY_ADDRESS, DEPLOYER_PRIVATE_KEY must all be set")

        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError("Cannot connect to Sepolia RPC")

        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=ABI,
        )
        self.account = self.w3.eth.account.from_key(private_key)

    def submit_audit(
        self,
        contract_identifier: str,
        risk_score: int,
        summary: str,
        report_hash: str,
    ) -> str:
        """Submit an audit record on-chain. Returns the transaction hash."""
        print(f"[DEBUG] connected={self.w3.is_connected()}")
        print(f"[DEBUG] chain_id={self.w3.eth.chain_id}")
        print(f"[DEBUG] contract={self.contract.address}")
        print(f"[DEBUG] submit identifier={repr(contract_identifier)}")
        contract_id = self.contract.functions.stringToId(contract_identifier).call()
        print(f"[DEBUG] submit contractId={contract_id.hex()}")

        nonce     = self.w3.eth.get_transaction_count(self.account.address)
        gas_price = self.w3.eth.gas_price
        print(f"[DEBUG] account={self.account.address}")
        print(f"[DEBUG] nonce={nonce}, gasPrice={gas_price}")
        print(f"[DEBUG] contractId={contract_id.hex()}, riskScore={risk_score}")

        tx = self.contract.functions.submitAudit(
            contract_id,
            risk_score,
            summary,
            report_hash,
        ).build_transaction({
            "from":     self.account.address,
            "nonce":    nonce,
            "gas":      1000000,
            "gasPrice": gas_price,
        })
        signed  = self.account.sign_transaction(tx)
        raw     = signed.raw_transaction if hasattr(signed, 'raw_transaction') else signed.rawTransaction
        tx_hash = self.w3.eth.send_raw_transaction(raw)
        self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        return self.w3.to_hex(tx_hash)

    def get_latest_audit(self, contract_identifier: str) -> dict:
        """Return the most recent audit record for a contract identifier."""
        print(f"[DEBUG] get_latest_audit identifier={repr(contract_identifier)}")
        contract_id = self.contract.functions.stringToId(contract_identifier).call()
        print(f"[DEBUG] get_latest_audit contractId={contract_id.hex()}")
        result = self.contract.functions.getLatestAudit(contract_id).call()
        return {
            "submitter":   result[0],
            "risk_score":  result[1],
            "summary":     result[2],
            "report_hash": result[3],
            "timestamp":   result[4],
        }

    def get_audit_count(self, contract_identifier: str) -> int:
        """Return total number of audits for a contract."""
        contract_id = self.contract.functions.stringToId(contract_identifier).call()
        return self.contract.functions.getAuditCount(contract_id).call()

    def get_audit_at(self, contract_identifier: str, index: int) -> dict:
        """Return audit record at a specific index."""
        contract_id = self.contract.functions.stringToId(contract_identifier).call()
        result = self.contract.functions.getAuditAt(contract_id, index).call()
        return {
            "index":       index,
            "submitter":   result[0],
            "risk_score":  result[1],
            "summary":     result[2],
            "report_hash": result[3],
            "timestamp":   result[4],
        }

    def verify_report(self, contract_identifier: str, report_hash: str) -> dict:
        """Check whether a report hash matches any on-chain record."""
        contract_id = self.contract.functions.stringToId(contract_identifier).call()
        matched, index = self.contract.functions.verifyReport(contract_id, report_hash).call()
        return {"matched": matched, "index": index}
