# Smart Audit Registry

An AI-powered smart contract security auditing platform that analyzes Solidity source code, stores results on-chain (Sepolia testnet), and uses IPFS for immutable report storage.

## Overview

Users upload a `.sol` file or provide a verified contract address. The system runs an AI analysis, generates a risk score and vulnerability report, uploads the full report to IPFS via Pinata, and submits an immutable audit record to the blockchain.

```
Upload .sol / Contract Address
        ↓
   AI Analysis (OpenAI)
        ↓
 IPFS Upload (Pinata)
        ↓
  On-chain Record (Sepolia)
        ↓
  View & Verify Report
```

## Features

- **Submit Audit** — upload a `.sol` file or fetch source from Etherscan by contract address
- **View Record** — query all historical audit records for any contract
- **Verify Report** — verify a report hash against the on-chain record
- **Full Report Viewer** — view detailed vulnerability findings with severity breakdown

## Smart Contract

Deployed on Sepolia testnet: [`0x1097fdb5c04bF892D4754786c8d3d0bd24F29247`](https://sepolia.etherscan.io/address/0x1097fdb5c04bF892D4754786c8d3d0bd24F29247)

Key design decisions:
- Uses `bytes32` (keccak256) as identifier — supports both contract addresses and filenames
- Stores full audit history per contract (no overwriting)
- `verifyReport` function for tamper-proof verification
- Helper functions: `addressToId`, `stringToId`

## Tech Stack

| Layer | Technology |
|---|---|
| Smart Contract | Solidity 0.8.20, Sepolia testnet |
| Backend | Python, FastAPI, Web3.py |
| AI Analysis | OpenAI GPT-4, tree-sitter-solidity |
| Storage | IPFS via Pinata v3 API |
| Frontend | React, Vite, ethers.js |

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- API keys: OpenAI, Etherscan, Pinata
- Sepolia wallet with test ETH

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in your API keys
python -m uvicorn app:app --host 127.0.0.1 --port 8080
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

### Environment Variables

```env
OPENAI_API_KEY=
ETHERSCAN_API_KEY=
PINATA_JWT=
PINATA_GATEWAY=https://your-gateway.mypinata.cloud
SEPOLIA_RPC_URL=
AUDIT_REGISTRY_ADDRESS=0x1097fdb5c04bF892D4754786c8d3d0bd24F29247
DEPLOYER_PRIVATE_KEY=
```

## Project Structure

```
smart-audit-registry/
├── contracts/
│   ├── AuditRegistry.sol       # Main registry contract
│   └── VulnerableToken.sol     # Test contract
├── backend/
│   ├── app.py                  # FastAPI routes
│   ├── audit_engine/           # AI analysis logic
│   ├── blockchain/             # Web3 / contract interaction
│   └── services/               # IPFS, Etherscan integrations
└── frontend/
    └── src/
        ├── pages/              # Submit, View, Verify, Report
        └── components/         # AuditResult, WalletConnect
```
