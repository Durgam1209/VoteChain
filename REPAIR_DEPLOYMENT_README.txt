VOTECHAIN CONTRACT CONFIGURATION + DEPLOYMENT REPAIR

WHAT THIS PATCH CHANGES
- config.py trims CONTRACT_ADDRESS from .env.
- core/blockchain.py falls back to blockchain/deployment.json when CONTRACT_ADDRESS is blank.
- It checks RPC connectivity, chain ID, and deployed bytecode before any contract operation.
- Receipt verification uses Web3.py's DISCARD enum, not errors=0.
- The Hardhat deploy script refuses non-local chain IDs and writes the new address and chain ID to blockchain/deployment.json.

IMPORTANT
Your previously confirmed transaction at block 4 has zero logs and was sent to an address with no bytecode. It cannot be converted into a contract ballot/event. The patch does not modify your database, keys, existing deployment file, or old transaction.

APPLY
1. Stop Streamlit with Ctrl+C. Keep your current Hardhat node running for now.
2. Extract this ZIP somewhere separate. Copy these files into your existing VoteChain project, preserving folder paths and choosing overwrite:
   config.py
   core/blockchain.py
   blockchain/scripts/deploy.js
   .env.example (reference only; do not overwrite your real .env)
3. Ensure .env has RPC_URL=http://127.0.0.1:8545 and CHAIN_ID=31337. CONTRACT_ADDRESS may be blank; blank now means use blockchain/deployment.json.
4. In a NEW PowerShell terminal:
   cd C:\Users\DurgaM\Downloads\VoteChain\VoteChain\blockchain
   npm run compile
   npm run deploy
   This deploys a fresh contract to the currently running local node and updates blockchain/deployment.json.
5. In the project-root terminal:
   cd C:\Users\DurgaM\Downloads\VoteChain\VoteChain
   python -c "from core.blockchain import load_contract; w,c=load_contract(); print('CHAIN',w.eth.chain_id,'CONTRACT',c.address,'BYTECODE',len(w.eth.get_code(c.address)))"
   python -m pytest -q
   python -m streamlit run app.py
6. Create/use an election in the app. Existing elections on the previous in-memory chain may need initializeElection again on the newly deployed contract. Do not delete SQLite. If initialization says election already exists, it is already initialized.
7. Cast ONE new test ballot, then verify its new transaction hash and commitment. Do not reuse the old zero-log transaction as a ballot proof.

DO NOT
- Delete data/, data/keys/, votechain.sqlite3, or deployment.json.
- Restart the Hardhat node after deploying; a restart clears its in-memory chain and requires redeployment.
- Put private keys or passwords into shared files.

NOTE
This is a local competition/demo setup, not production election infrastructure.
