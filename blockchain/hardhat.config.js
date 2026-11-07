require("@nomicfoundation/hardhat-toolbox");

const sepoliaUrl = process.env.SEPOLIA_RPC_URL;
const deployerKey = process.env.DEPLOYER_PRIVATE_KEY;

module.exports = {
  solidity: "0.8.24",
  networks: {
    localhost: { url: "http://127.0.0.1:8545", chainId: 31337 },
    ...(sepoliaUrl && deployerKey ? {
      sepolia: { url: sepoliaUrl, accounts: [deployerKey], chainId: 11155111 }
    } : {})
  }
};
