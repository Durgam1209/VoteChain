const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const network = await hre.ethers.provider.getNetwork();
  if (network.chainId !== 31337n) {
    throw new Error(`Refusing deployment: expected local Hardhat chain 31337, got ${network.chainId}`);
  }

  const Voting = await hre.ethers.getContractFactory("Voting");
  const voting = await Voting.deploy();
  await voting.waitForDeployment();

  const address = await voting.getAddress();
  const output = {
    address,
    chainId: Number(network.chainId),
    network: "hardhat-localhost"
  };
  const deploymentPath = path.join(__dirname, "..", "deployment.json");
  fs.writeFileSync(deploymentPath, JSON.stringify(output, null, 2) + "\n", "utf8");
  console.log("VoteChain deployed successfully:", output);
  console.log("Deployment file:", deploymentPath);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
