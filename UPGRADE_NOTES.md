# VoteChain — Competition Upgrade (Priorities 1–4)

This upgrade builds on the candidate/election management package. It preserves the existing Streamlit + Python + SQLite + Paillier + Solidity/Hardhat + Web3.py architecture and does not change the deployed Solidity contract or its ABI.

## 1. Public blockchain verification
- Added a **Public verification** tab to the signed-out landing screen; no VoteChain account is required.
- A verifier enters an election ID, transaction hash, and SHA-256 ballot commitment.
- The app checks the transaction receipt, confirms it targeted the deployed VoteChain contract, decodes the `BallotRecorded` event, and matches both the election key and commitment.
- Successful verification displays the block number and transaction hash.
- This verifies the supplied commitment event, not voter eligibility, ballot correctness, or a voter's choice.

## 2. Election start/end scheduling
- Election creation now requires start and end date/time values in the admin UI.
- Admins can edit the schedule before the first ballot is recorded.
- The application blocks voting before the start time and at/after the end time.
- Manually closed elections remain closed.
- Existing elections migrated from earlier versions keep null schedule values and therefore retain their previous behavior (open until manually closed) until an administrator sets a schedule.
- Schedule values use the local machine's time zone as a naive local datetime in this local demo. Keep the app host's time zone consistent with the election operator's intended time zone.

## 3. Voter eligibility management
- New self-registered accounts are created as **pending approval**.
- Pending accounts cannot authenticate into the voter workspace or submit ballots.
- Admins have a **Voter eligibility** page to approve or suspend accounts.
- The voting service independently checks the current SQLite eligibility flag before creating a ballot.
- Existing accounts are migrated as eligible to preserve the previously working demo. Existing admin and demo-voter credentials are not reset.

## 4. Transaction failure reconciliation
- A local pending-ballot recovery record is created before broadcasting a blockchain transaction.
- The transaction hash is saved as soon as it is available, before waiting for confirmation.
- A confirmed transaction is finalized into the existing local ballot and voter-participation tables in one SQLite transaction.
- If the app loses the confirmation/finalization step, the admin **Audit & results** page exposes the pending item and a **Reconcile this transaction** action.
- Confirmed receipts are finalized; failed receipts are marked failed and allow the voter to retry; unavailable receipts remain waiting.
- A failed submission row is reused on retry to avoid unique-nullifier conflicts.
- Do not ask a voter to retry while a record is in `PENDING` or `REVIEW`. Reconcile first.

## Database compatibility and deployment
- `database.db.init_db()` applies additive SQLite migrations automatically at app startup: `voters.is_eligible`, `elections.start_at`, `elections.end_at`, and `pending_ballots`.
- No existing voter password, election, ballot, commitment, nullifier, or candidate profile is rewritten by the migration.
- The Solidity contract is unchanged. No contract recompilation or redeployment is required for this upgrade.
- The ZIP intentionally excludes runtime `data/`, `.env`, Paillier keys, nullifier secret, `blockchain/deployment.json`, Hardhat artifacts, `node_modules`, and local database files.
- Back up `data/` and `blockchain/deployment.json` before replacing project files. Keep the same local Hardhat node/deployment for the existing database.

## Validation
- Python compilation was checked.
- 19 unit tests passed in the packaging environment using test-only dependency shims because this environment did not have the project's external Python packages installed and could not reach package indexes. This is not a substitute for running `pytest -q` in the user's `.venv` with the real dependencies.
- Live Hardhat + Web3 event verification and the Streamlit UI must be smoke-tested on the user's Windows machine against the existing deployment.
