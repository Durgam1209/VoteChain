"""Export a privacy-conscious audit CSV for an election (no voter IDs)."""
import argparse
import csv
from pathlib import Path

from core.voting import get_election, election_ballots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("election_id")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    election = get_election(args.election_id)
    if not election:
        parser.error("Election ID was not found in the local database.")
    output = Path(args.output or f"{args.election_id}_audit.csv")
    ballots = election_ballots(args.election_id)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["election_id", "created_at", "commitment", "tx_hash"])
        writer.writeheader()
        for ballot in ballots:
            writer.writerow({
                "election_id": args.election_id,
                "created_at": ballot.get("created_at", ""),
                "commitment": ballot["commitment"],
                "tx_hash": ballot["tx_hash"] or "",
            })
    print(f"Exported {len(ballots)} audit records to {output.resolve()}")


if __name__ == "__main__":
    main()
