# VoteChain college UI — operator notes

## What changed
The original Streamlit application has been replaced with a role-aware college election interface. It uses the existing Python services and database schema; it does not migrate or reset the database.

## Navigation
### Administrator
- Overview: election counts, voter count, ballot count, and chain count summary.
- Elections: create elections and close open elections.
- Voter preview: exercise the ballot flow with the admin demo account.
- Audit & results: compare local/on-chain counts, inspect commitment and transaction references, and tally only after closure.

### Student voter
- My dashboard: election status and personal participation count.
- Cast your vote: candidate cards, one candidate selection, explicit review confirmation, encrypted submission and receipt references.
- Verify participation: shows whether the account's voting authorization has been used, without displaying a candidate choice.

## Existing backend functions used
- `core.authentication`: `authenticate`, `create_user`, `list_voters`
- `core.voting`: election lifecycle, ballot submission, participation lookup and ballot retrieval
- `core.tally`: commitment verification and aggregate tally
- `core.blockchain`: local contract connection and ballot count

## Run
Keep the local Hardhat node running in one terminal, then from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

## Known constraints
- Candidate records currently contain names only; cards therefore use generated initials rather than fabricated candidate photos or manifestos.
- There is no election date/time, department, candidate biography, or manifesto field in the current database schema.
- The admin dashboard uses the existing voter table and does not add bulk voter import or role management.
- The audit page compares counts and verifies ballot commitments during tally. It does not independently prove voter eligibility, ballot validity, or end-to-end election integrity.
