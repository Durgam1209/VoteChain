# VoteChain security model and honest claims

## What this prototype demonstrates
- Passwords are stored as bcrypt hashes.
- Ballots are encoded as one-hot vectors and Paillier-encrypted before local storage.
- Ciphertexts can be homomorphically aggregated and the aggregate is decrypted for the demo tally.
- A SHA-256 commitment to each encrypted ballot is recorded in the local database and anchored on a local EVM chain.
- Election-scoped nullifiers are used by the contract to reject a repeated nullifier.
- The application checks the local voter-eligibility record before attempting another vote.
- The audit screen can compare local and on-chain counts and inspect public transaction metadata.

## What this prototype does not prove
- It does not provide formal voter anonymity or unlinkability. A nullifier is a pseudonymous duplicate-prevention value, not a zero-knowledge proof.
- It does not prove a ballot is a valid one-hot vector on-chain. The contract stores commitments, not a ZK ballot-validity proof.
- The local tally process trusts the local database and locally stored Paillier private key.
- The first Hardhat account is used as the transaction sender in the local adapter. This is a development convenience, not voter authentication on-chain.
- The contract does not independently enforce voter eligibility, voting windows, or election closure.
- A matching count and valid commitments are not an end-to-end verifiability proof and do not rule out every attack.
- The system is not coercion-resistant, independently audited, or certified for public elections.

## Protect local runtime data
- Never commit `.env`, `data/`, `data/keys/`, `deployment.json`, or Hardhat private keys.
- Back up `data/keys/nullifier_secret.txt` together with the database. Losing or rotating this secret changes future nullifiers and can complicate reconciliation.
- Protect `data/keys/paillier_keys.json`; it contains the private decryption key.
- Do not publish real voter details, ballot receipts, or private keys in screenshots or recordings.
- Use fresh demo accounts and a fresh local chain for public demonstrations where practical.

## Next security milestones (not implemented by this ZIP)
1. Independent eligibility authority and authenticated enrollment.
2. Anonymous credentials or blind-signature-based authorization.
3. Zero-knowledge proof of ballot well-formedness and eligibility.
4. Threshold Paillier key generation/decryption with independent trustees.
5. On-chain election state machine enforcing open/closed windows and authorized submission.
6. Transaction relayer design with abuse controls and independently authenticated signing.
7. Independent cryptographic review, threat modeling, penetration testing, and operational audit.
- The preflight eligibility check improves the normal single-user flow, but it is not a complete concurrency-control protocol for multiple simultaneous application workers. The SQLite uniqueness constraint remains a last-line local guard; a concurrent race after an on-chain submission can still require manual reconciliation.

## Roadmap update included in this package
- New registrations are pending until an administrator approves them; existing accounts remain eligible during migration for demo continuity.
- The Python voting service checks eligibility and the election schedule before sending a transaction.
- The signed-out public verification page decodes a confirmed `BallotRecorded` event and matches the election key and commitment supplied by the verifier.
- A local pending-ballot recovery queue records transaction hashes and allows an administrator to reconcile confirmed/failed receipts.
- These are application-layer controls. The unchanged Solidity contract does not independently enforce the voting schedule or voter eligibility. Public event verification is not a proof of ballot validity, voter anonymity, or complete election correctness.
