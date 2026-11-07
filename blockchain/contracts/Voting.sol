// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * VoteChain demo contract.
 * Stores only election-scoped nullifiers and ballot commitments.
 * It does not store voter identities, plaintext votes or encrypted ballots.
 *
 * Prototype warning: the first local Hardhat account is the transaction sender
 * in the demo adapter. Production requires a properly designed relayer and
 * anonymous credential / ZK authorization flow.
 */
contract Voting {
    address public immutable owner;

    struct ElectionLedger {
        uint256 ballotCount;
        bool exists;
    }

    mapping(bytes32 => ElectionLedger) public elections;
    mapping(bytes32 => mapping(bytes32 => bool)) public usedNullifiers;
    mapping(bytes32 => mapping(bytes32 => bytes32)) public commitments;

    event BallotRecorded(
        bytes32 indexed electionKey,
        bytes32 indexed nullifier,
        bytes32 commitment,
        uint256 timestamp
    );

    constructor() {
        owner = msg.sender;
    }

    function initializeElection(bytes32 electionKey) external {
        require(msg.sender == owner, "Only owner");
        require(!elections[electionKey].exists, "Election exists");
        elections[electionKey] = ElectionLedger(0, true);
    }

    function recordBallot(
        bytes32 electionKey,
        bytes32 commitment,
        bytes32 nullifier
    ) external {
        require(elections[electionKey].exists, "Unknown election");
        require(commitment != bytes32(0), "Empty commitment");
        require(nullifier != bytes32(0), "Empty nullifier");
        require(!usedNullifiers[electionKey][nullifier], "Already voted");

        usedNullifiers[electionKey][nullifier] = true;
        commitments[electionKey][nullifier] = commitment;
        elections[electionKey].ballotCount += 1;

        emit BallotRecorded(electionKey, nullifier, commitment, block.timestamp);
    }

    function ballotCount(bytes32 electionKey) external view returns (uint256) {
        return elections[electionKey].ballotCount;
    }
}
