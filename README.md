# Smart Audit Registry

An AI-powered smart contract security auditing platform built on Sepolia testnet.
Submit any Solidity contract — the system runs a multi-agent AI analysis, generates a risk score,
stores the full report on IPFS, and writes an immutable audit record to the blockchain.

---

## How It Works

```
User submits a contract address or .sol file
        ↓
1. Frontend  →  sends request to backend (FastAPI)

2. Backend   →  fetches source code from Etherscan API
                (or reads uploaded file directly)

3. Backend   →  runs Multi-Agent AI analysis
   ├── Agent 1: RAG Auditor      ─┐
   ├── Agent 2: Logic Auditor     ├── run in parallel per function
   ├── Agent 3: LowLevel Auditor ─┘
   ├── Agent 4: Debate Agent     →  merges & deduplicates findings
   └── Agent 5: Validator        →  filters false positives + scores

4. Backend   →  generates full JSON report

5. Backend   →  uploads report to IPFS via Pinata
                gets back IPFS hash (bafkrei...)

6. Backend   →  connects to Sepolia via Infura RPC
                calls AuditRegistry.submitAudit()
                writes: contract address + risk score + IPFS hash

7. Sepolia   →  transaction confirmed, permanently stored on-chain

8. Backend   →  returns result to frontend

9. Frontend  →  displays audit result, score, findings, IPFS link, tx hash
```

---

## Services Used

| Service | Purpose |
|---------|---------|
| Etherscan API | Fetch verified contract source code |
| OpenAI GPT-4o-mini | Power the 5 AI agents |
| Pinata / IPFS | Store full audit report (immutable) |
| Infura | Connect to Sepolia blockchain via RPC |
| AuditRegistry contract | Permanent on-chain audit records |

---

## Multi-Agent AI System

### Agent 1 — RAG Auditor
Uses a local knowledge base (ConsenSys Smart Contract Security Best Practices, 79 files)
indexed with FAISS vector search. Retrieves relevant security patterns before analyzing each function.

### Agent 2 — Logic Auditor
Specializes in access control, privilege escalation, and business logic flaws.
Checks who can call what, whether state transitions are correct, and trust assumptions.

### Agent 3 — LowLevel Auditor
Specializes in arithmetic issues, reentrancy, unchecked return values, inline assembly,
gas griefing, and low-level call patterns.

### Agent 4 — Debate Agent
Sees all findings from Agents 1–3. Deduplicates overlapping findings, adds `confirmed_by`
confidence field (how many agents independently found each issue), and filters obvious false positives.

### Agent 5 — Validator (Critic + Scorer combined)
Reviews every finding against the actual function code. Rejects false positives using explicit rules
(e.g. `nonReentrant` present → reject reentrancy, `require(success)` present → reject unchecked return).
Simultaneously scores the contract based on confirmed findings and contract context.

---

## Scoring System

Risk score uses a **diminishing returns formula** — each finding takes a fraction of remaining headroom:

```
score += (100 - score) × weight

Weights:
  HIGH   = 0.20   →  1st HIGH: 20pts, 2nd: +16pts, 3rd: +13pts ...
  MEDIUM = 0.08
  LOW    = 0.03
```

The formula score is the **baseline**. The Validator agent can adjust it **up by at most +20**
based on real-world impact (e.g. contract holds user ETH + reentrancy can drain it → score increases).
The score can never go below the baseline if findings exist.

### Risk Labels

| Score | Label |
|-------|-------|
| 0 | Safe |
| 1–20 | Low Risk |
| 21–50 | Medium Risk |
| 51–75 | High Risk |
| 76–100 | Critical Risk |

---

## Proxy Contract Detection

Upgradeable proxy contracts (USDC, AAVE, etc.) are automatically detected and skipped.
The proxy infrastructure (`delegatecall`, fallback) is intentional design, not a vulnerability.
Score = 0, user is told to audit the implementation contract instead.

---

## Smart Contract

AuditRegistry deployed on Sepolia:
[`0x1097fdb5c04bF892D4754786c8d3d0bd24F29247`](https://sepolia.etherscan.io/address/0x1097fdb5c04bF892D4754786c8d3d0bd24F29247)

- Stores full audit history per contract (no overwriting)
- `verifyReport()` for tamper-proof verification against IPFS hash
- Uses `bytes32` (keccak256) as identifier — supports addresses and filenames

---

## Features

- **Submit Audit** — contract address (Etherscan verified) or upload `.sol` file directly
- **Connect Wallet** — MetaMask required to submit (writes to blockchain)
- **View Record** — query all historical audit records for any contract
- **Verify Report** — verify a report hash matches the on-chain record (tamper detection)
- **Full Report Viewer** — detailed findings with severity, description, and line numbers

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Smart Contract | Solidity 0.8.20, Sepolia testnet |
| Backend | Python, FastAPI, Web3.py |
| AI Analysis | OpenAI GPT-4o-mini, tree-sitter-solidity |
| RAG | FAISS vector index, ConsenSys knowledge base |
| Storage | IPFS via Pinata |
| Frontend | React, Vite, ethers.js |

---

## Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- MetaMask wallet with Sepolia test ETH ([faucet](https://sepoliafaucet.com))
- API keys: OpenAI, Etherscan, Pinata, Infura

### Backend

```bash
cd backend
pip install -r requirements.txt

# Create .env file (see Environment Variables below)
cp .env.example .env

python3 -m uvicorn app:app --host 127.0.0.1 --port 8080
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

---

## Environment Variables

Create `backend/.env`:

```env
# OpenAI (required for AI analysis)
OPENAI_API_KEY=sk-...

# Etherscan (free at etherscan.io)
ETHERSCAN_API_KEY=...

# Pinata IPFS (free at pinata.cloud)
PINATA_JWT=...
PINATA_GATEWAY=https://your-gateway.mypinata.cloud
PINATA_API_KEY=...
PINATA_API_SECRET=...

# Sepolia RPC (free at infura.io or alchemy.com)
SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY

# Deployed AuditRegistry contract
AUDIT_REGISTRY_ADDRESS=0x1097fdb5c04bF892D4754786c8d3d0bd24F29247

# Sepolia wallet private key (testnet only, no real funds)
DEPLOYER_PRIVATE_KEY=...
```

---

## Project Structure

```
smart-audit-registry/
├── contracts/
│   ├── AuditRegistry.sol          # On-chain audit registry
│   ├── SafeToken.sol              # Reference safe contract (for testing)
│   └── VulnerableToken.sol        # Intentionally vulnerable (for testing)
├── backend/
│   ├── app.py                     # FastAPI routes
│   ├── audit_engine/
│   │   ├── analyzer.py            # 5-agent multi-agent pipeline
│   │   ├── parser.py              # Solidity function parser (tree-sitter)
│   │   └── report.py              # Report generation + scoring formula
│   ├── services/
│   │   ├── etherscan.py           # Fetch source from Etherscan
│   │   ├── ipfs.py                # Upload to Pinata/IPFS
│   │   └── rag.py                 # FAISS vector search
│   ├── blockchain/
│   │   └── registry.py            # Web3 contract interaction
│   └── knowledge_base/            # ConsenSys security knowledge (79 files)
└── frontend/
    └── src/
        ├── pages/
        │   ├── SubmitAudit.jsx    # Submit page
        │   ├── ViewAudit.jsx      # View on-chain records
        │   ├── VerifyReport.jsx   # Verify report hash
        │   └── ReportView.jsx     # Full report viewer
        └── components/
            └── AuditResult.jsx    # Audit result display
```

---

## Testing

Recommended contracts for verifying accuracy:

| Contract | Expected Score | Why |
|----------|---------------|-----|
| `SafeToken.sol` (upload) | 0–20 | OZ patterns, ^0.8.x, CEI, nonReentrant |
| `VulnerableToken.sol` (upload) | 50+ | Reentrancy, overflow, missing access control |
| WETH `0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14` | 0–20 | Simple, safe contract |
| USDC `0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238` | 0 (proxy) | Proxy detected, skipped |
