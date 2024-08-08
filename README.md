Hyperledger Indy and Aries POC: KYC System

Overview
This repository contains a Proof of Concept (POC) for a Know Your Customer (KYC) system built using Hyperledger Indy and Hyperledger Aries. The system is designed to manage and verify identities with blockchain-based technology. It supports functionalities for identity creation, management, verification, and access management, and integrates document hashing for secure storage.

 Features
- Identity Creation: Register new users with detailed personal information and documents.
- Identity Management: Update and revoke identities as required.
- Identity Verification: Verify user identities through a decentralized ledger.
- Document Hashing: Hash and store document hashes securely on the blockchain.

 Technologies Used
- Hyperledger Indy: Provides a decentralized identity management framework.
- Hyperledger Aries: Offers the communication layer for exchanging credentials and verifiable claims.
- Docker: Used for containerization of Aries Cloud Agent.

Prerequisites
1. Docker: Ensure you have Docker installed on your system.
2. Node.js and npm: Required for running some of the setup scripts.
3. Python: Required for running Aries Cloud Agent.
4. Hyperledger Indy and Aries repositories: Clone the necessary repositories from GitHub.
5. Ngrok and Jq
6. Mobile Wallet: BC Gov Wallet


* First, clone the aries repository to your project directory:
git clone https://github.com/hyperledger/aries-cloudagent-python.git cd aries-cloudagent-python

* Set Up the VON Network
The VON (Verifiable Organizations Network) network is required for the demo. Follow these steps to build and start the VON network:
Clone the von network repository
Then build the images for von-network and start it.
git clone https://github.com/bcgov/von-network.git cd von-network ./manage build ./manage start

* Navigate to the demo folder in the cloned Aries Cloud Agent repository:
cd ../aries-cloudagent-python/demo

* Use ngrok and create a tunnel to the local machine
ngrok http 8020
* In a different terminal, navigate to the project directory, and install an indy tails server. The Indy Tails Server manages the tails files required for credential revocation. When running on a mobile agent, the tails server ensures that the mobile agent can access and manage the revocation registry efficiently.
git clone https://github.com/bcgov/indy-tails-server.git cd indy-tails-server/docker ./manage build ./manage start
* Now navigate to the demo directory and run the following to start the bank agent with revocation function
TAILS_NETWORK=docker_tails-server LEDGER_URL=http://test.bcovrin.vonx.io ./run_demo faber --aip 10 --revocation --events

We are using OpenAPI to send instructions to each agent. The port predefined in the code is
* Faber: 8021
* Alice: 8031
You can access them at https://localhost:<port>

* Once the program successfully compiles and run, you should see a static QR code, which connect the bank agent to the mobile agent:

* Scan the QR code using the mobile wallet, and you should be able to connect the mobile agent with the bank agent

* You will then see a list of options on your terminal, where the bank agent is running:

* To issue a credential, type 1 and press enter on your terminal. (Currently, the attributes for the credential have been hard coded in the code, for further development, these attributes would be inputted by the bank agent on a UI). 

* Accept the credential offer on your mobile agent. Once the terminal gives you the following message, the credential would have been succesfully added to the mobile wallet.

* In order to verify a proof, type 2 from the menu, and press enter. This would send a proof request to the mobile agent.

* Once you send the proof from the mobile agent to the bank agent, it will check the values, and if they match, it should say “Proof = true”

* For revocation, run the program with revocation, and you will see the options menu, but with additional options. Type 5 and press enter to revoke the credential.


 Contributing

Contributions are welcome! Please open issues or submit pull requests for improvements.

