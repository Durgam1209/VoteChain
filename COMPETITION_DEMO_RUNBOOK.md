# VoteChain competition demo runbook

## 4-minute demo story

### 1. Problem (20 seconds)
Campus elections need a clear voting workflow, controlled eligibility, privacy-aware ballot handling, and a way to inspect submitted ballot commitments.

### 2. Product (30 seconds)
VoteChain is an educational prototype combining bcrypt account authentication, Paillier-encrypted one-hot ballots, SHA-256 commitments, a local Solidity ledger, scheduled voting windows, administrator-controlled voter eligibility, and transaction recovery.

### 3. Live workflow (2 minutes)
1. Start the Hardhat node and deploy only if this is a fresh local chain.
2. Start Streamlit and sign in as `admin`.
3. Show **Voter eligibility**. Existing demo voters are already eligible; new registrations appear pending until approved.
4. In **Elections**, create a short demo election with a start time now and an end time several minutes later. Add candidates and candidate profiles.
5. Sign out and sign in as `voter1`; cast a ballot and show its commitment, transaction hash, block number, and confirmation.
6. Open the signed-out **Public verification** tab and verify using the election ID, transaction hash, and commitment from the receipt.
7. Sign in as admin and show the local/on-chain count comparison and audit CSV.
8. If a pending transaction exists, show **Reconcile this transaction**. Otherwise explain that this is the recovery path for interrupted confirmation/finalization.
9. Close the election and calculate the aggregate tally.

### 4. Explain what blockchain adds (30 seconds)
The application records a commitment event on the local EVM ledger. The public verification screen can inspect a transaction receipt and confirm that the contract emitted the matching election key and commitment. This creates an independently inspectable transaction reference; it does not prove that the encrypted ballot is a valid one-hot vote or that voter eligibility was enforced on-chain.

### 5. Be honest about limitations (20 seconds)
This is a local prototype, not a certified election system. The app enforces schedule and eligibility rules in its Python/SQLite service, but the contract does not independently enforce them. The local Hardhat account submits transactions. It does not provide formal unlinkability, coercion resistance, ZK ballot-validity proofs, threshold decryption, or production key custody.

## Demo accounts
- Admin: `admin` / `VoteChain-Admin-2026`
- Voters: `voter1` through `voter4` / `VoteChain-Demo-2026`

These credentials are for the local demo only. Do not use them on a public deployment.

## Startup checklist (Windows PowerShell)

Terminal 1 — Hardhat node:
```powershell
cd .\blockchain
npm run node
```

Terminal 2 — deploy only on a fresh chain or when intentionally redeploying:
```powershell
cd .\blockchain
npm run deploy
```

Terminal 3 — Python app:
```powershell
.\.venv\Scripts\Activate.ps1
python scripts\health_check.py
streamlit run app.py
```

Do not redeploy a fresh contract against an existing local DB unless you understand that a restarted Hardhat node has a new chain state. Existing election records may refer to elections not initialized on the new chain.

## If a vote fails or times out
- Check that the Hardhat node terminal is still running.
- Run `python scripts\health_check.py` from the project root.
- Do not repeatedly click Submit after a transaction-submitted or reconciliation message.
- Sign in as admin, open **Audit & results**, select the election, and inspect **Pending transaction reconciliation**.
- Reconcile a pending transaction. If the receipt is confirmed, the app finalizes the ballot locally. If the receipt failed, the pending record is marked failed and the voter can retry. If the receipt is not yet available, wait and retry reconciliation later.
