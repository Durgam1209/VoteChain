from database.db import init_db
from core.authentication import create_user
from core.voting import create_election

def main():
    init_db()
    try:
        create_user("admin", "Demo Administrator", "VoteChain-Admin-2026", True, eligible=True)
        print("Created admin: admin / VoteChain-Admin-2026")
    except ValueError as e:
        print("Admin account:", e)
    for voter_id, name in [
        ("voter1", "Voter One"), ("voter2", "Voter Two"),
        ("voter3", "Voter Three"), ("voter4", "Voter Four")
    ]:
        try:
            create_user(voter_id, name, "VoteChain-Demo-2026", False, eligible=True)
            print(f"Created {voter_id} / VoteChain-Demo-2026")
        except ValueError:
            print(f"{voter_id} already exists")
    try:
        create_election("DBIT-2026-DEMO", "DBIT Student Council Demo",
                        ["Candidate A", "Candidate B", "Candidate C"])
        print("Created demo election DBIT-2026-DEMO")
    except Exception as e:
        print("Demo election:", e)

if __name__ == "__main__":
    main()
