# VoteChain — Private ballots. Verifiable elections.

A local institutional-election MVP demonstrating:
- Password-hashed voter accounts
- One-vote-per-voter enforcement in the application database
- Paillier encrypted one-hot ballots
- Homomorphic aggregation and authorized aggregate decryption
- SHA-256 ballot commitments
- Solidity contract storing election-scoped nullifiers and commitments
- Streamlit voter/admin/audit interface

## Important security scope

This is an educational prototype, not a production election system and not certified for public/government elections. The demo uses a local Hardhat chain, a local SQLite database, and a locally stored Paillier private key. The demo nullifier secret is generated locally and must be backed up; it is not a formal anonymous credential. The transaction sender is the first local Hardhat account. Self-registration is available for demonstration, but new accounts remain pending until an administrator approves voter eligibility. Existing demo accounts retain their eligibility during migration.

The prototype does not provide formal unlinkability, coercion resistance, end-to-end verifiability proofs, zero-knowledge ballot-validity proofs, threshold decryption, secure key custody, or protection against compromised voter devices. Do not use it for real elections.

## Requirements

- Python 3.12 recommended
- Node.js LTS and npm
- VS Code

## 1. Python environment (Windows PowerShell)

From the VoteChain root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Install and run local blockchain

```powershell
cd blockchain
npm install
npm run compile
```

Open a second terminal in `VoteChain\blockchain`:

```powershell
npm run node
```

Keep this terminal running. In the first terminal:

```powershell
npm run deploy
```

The deploy script writes `blockchain/deployment.json`. Elections created by an administrator are initialized on-chain by the application.

## 3. Start the Python app

Open another terminal at the VoteChain root:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/setup_demo.py
streamlit run app.py
```

Open the local Streamlit URL shown in the terminal.

Demo accounts (change these before any shared demo):
- Admin: `admin` / `VoteChain-Admin-2026`
- Voters: `voter1` through `voter4` / `VoteChain-Demo-2026`

## 4. Demo sequence

1. Sign in as admin.
2. Use the pre-created `DBIT-2026-DEMO` election.
3. Sign out and sign in as voter1; cast a ballot.
4. Repeat with voter2 and voter3.
5. Sign back in as admin.
6. Close the election in Election administration.
7. In Audit & tally, compare local ballot count with on-chain ballot count.
8. Click Verify and calculate results.

The local database and blockchain must both be running for ballot submission.

## 5. Tests

From the project root with the virtual environment activated:

```powershell
pytest -q
```

The test suite covers password authentication, Paillier homomorphic tally, commitment verification and election creation. Blockchain integration should additionally be tested using the live local Hardhat node and the demo sequence above.

## Data and keys

Runtime data is created in `data/`, which is git-ignored:
- `votechain.sqlite3`
- `keys/paillier_keys.json`

The Paillier private key is stored locally for this demonstration. This is not acceptable key management for production.

## Architecture

- Streamlit: user interface
- Python: application logic
- SQLite: local eligibility state and encrypted ballots
- `phe`: Paillier encryption
- Solidity + Hardhat: local EVM ledger
- Web3.py: Python-to-contract integration

## Known prototype limitation

Election creation in the application initializes the corresponding election key on-chain. The demo contract still has a single owner account and is not a production authorization design.

---

## College UI upgrade (v1.1)

The refreshed Streamlit interface adds:
- A branded sign-in and registration screen
- Separate administrator and student-voter navigation
- An administrator overview with election, ballot, and voter metrics
- Election creation and closure workflows
- Candidate-card ballot selection with a review checkbox
- Participation status for voters
- Audit view comparing local ballot count with on-chain ballot count
- Verified aggregate tally after an election is closed
- Responsive styling and a consistent navy / blue / white visual system

### Updating an existing installation safely

1. Stop Streamlit with `Ctrl+C`.
2. Make a backup of your existing `data/` directory and `blockchain/deployment.json`.
3. Extract this ZIP into your existing `VoteChain` folder and allow `app.py` to be replaced.
4. Do **not** delete your existing `data/`, `blockchain/artifacts/`, `blockchain/deployment.json`, or `blockchain/node_modules/`.
5. Start the Hardhat node in `VoteChain\blockchain` if it is not already running:
   `npm run node`
6. From the VoteChain project root, activate `.venv` and run:
   `streamlit run app.py`

The upgrade intentionally does not include a SQLite database, generated Hardhat artifacts, deployment address, node_modules, or private keys. Those are installation-specific runtime files and must remain in your existing project.

### Demo account reminders

- Admin: `admin` / `VoteChain-Admin-2026`
- Voters: `voter1` through `voter4` / `VoteChain-Demo-2026`

Do not use these demo credentials for a public deployment. Change them before sharing the demo.

### Security note

This is still an educational local prototype. The new interface does not change the underlying security model. The app uses a local Paillier private key, a placeholder demo nullifier secret, and the first local Hardhat account as the transaction sender. It does not provide formal voter unlinkability, coercion resistance, zero-knowledge ballot-validity proofs, threshold decryption, or production key custody. A matching local/on-chain ballot count and successful commitment check are useful demo checks, not a complete proof that an election is secure or correct.

---

## Competition upgrade (v2.0)

See `UPGRADE_NOTES.md` for the complete change list, `SECURITY_MODEL.md` for accurate security claims and limitations, and `COMPETITION_DEMO_RUNBOOK.md` for the live presentation flow.

### New checks and tools

```powershell
python scripts/health_check.py
pytest -q
```

Export an election audit CSV (contains election ID, timestamps, commitments and transaction hashes; it does not include voter IDs or plaintext candidate selections):

```powershell
python scripts/export_audit.py DBIT-2026-DEMO
```

The app also offers an audit CSV download in the administrator audit screen. Successful ballot submissions display public transaction metadata such as block number, status and gas used.

### Runtime secret

The application now generates `data/keys/nullifier_secret.txt` on first vote if it does not exist. Keep this file backed up with the database and private Paillier key. Do not delete or rotate it casually. This local secret improves the demo over a hardcoded placeholder; it does not make the nullifier a formal anonymous credential.

## Candidate profiles and election information

The administrator can add election position/description details and candidate profiles from **Elections**. Candidate profiles support a photo (PNG/JPG/JPEG/WEBP, max 5 MB), position, department, academic year, manifesto, and campaign promises. Students see these details on the **Cast your vote** page. Candidate ordering is deliberately not editable after election creation because ballots encode a candidate index.

Demo administrator login: **`admin` / `VoteChain-Admin-2026`**. If the account does not exist in the selected database, run `python -m scripts.setup_demo` from the project root. If it already exists with a different password, setup_demo will not reset it.

---

## Competition upgrade — public verification, scheduling, eligibility, recovery

This package adds the first four roadmap priorities:

### Public blockchain verification
- The signed-out landing page has a **Public verification** tab.
- Enter the election ID, transaction hash, and ballot commitment to check the deployed contract's confirmed `BallotRecorded` event.
- A successful check shows the block number and transaction hash. The verifier does not need to sign in.

### Election scheduling
- Admins set a voting start and end time while creating an election.
- Admins can update the schedule before any ballot is recorded.
- Voting is blocked before the start time and at/after the end time. A manually closed election stays closed.
- Existing elections from earlier versions remain without a schedule until an admin edits them; they continue to rely on manual closure.

### Voter eligibility
- New self-registered accounts wait for admin approval.
- Admins use **Voter eligibility** to approve or suspend accounts.
- The authentication layer and voting service both enforce the eligibility flag.
- Existing accounts are migrated as eligible so the current demo credentials continue working.

### Transaction reconciliation
- A pending local recovery record is saved before a ballot transaction is sent.
- Transaction hashes are persisted before waiting for confirmation.
- Admins can reconcile pending transactions from **Audit & results**. Confirmed transactions are finalized locally; failed transactions are marked failed; unavailable receipts remain pending.
- If a voter sees a transaction-submitted/reconciliation message, do not retry the vote until the admin has reconciled it.

### Applying this update to an existing Windows installation
1. Stop Streamlit with `Ctrl+C`.
2. Back up the complete `data/` directory and `blockchain/deployment.json`.
3. Extract this ZIP into the existing `VoteChain` project folder and allow source files to be replaced.
4. Do not delete or replace `.venv/`, `data/`, `.env`, `blockchain/deployment.json`, `blockchain/artifacts/`, or `blockchain/node_modules/`.
5. Activate the existing virtual environment and run:

```powershell
python -m pip install -r requirements.txt
python -m compileall -q .
python -m pytest -q
python scripts/health_check.py
streamlit run app.py
```

6. Sign in as `admin` and check **Voter eligibility**, **Elections**, and **Audit & results**. Open the signed-out **Public verification** tab to verify a receipt.

The app automatically adds the new SQLite columns/tables at startup. Do not delete the database to apply this update.

### Schedule time-zone note
The local demo stores schedule values in the application host's local time. Keep the machine's time zone correct and consistent during the demonstration.
