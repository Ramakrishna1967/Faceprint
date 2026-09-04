import argparse
import json
import os
from pathlib import Path

ABI = [
    {"inputs": [{"internalType": "bytes32", "name": "fp", "type": "bytes32"}, {"internalType": "string", "name": "url", "type": "string"}], "name": "storeRecord", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "fp", "type": "bytes32"}], "name": "getRecord", "outputs": [{"internalType": "bytes32", "name": "fingerprint", "type": "bytes32"}, {"internalType": "address", "name": "submitter", "type": "address"}, {"internalType": "uint64", "name": "timestamp", "type": "uint64"}, {"internalType": "string", "name": "matchedUrl", "type": "string"}], "stateMutability": "view", "type": "function"},
]


def main():
    parser = argparse.ArgumentParser(description="Deploy FaceVerificationRegistry")
    parser.add_argument("--rpc-url", default=os.getenv("RPC_URL"), required=not os.getenv("RPC_URL"))
    parser.add_argument("--private-key", default=os.getenv("PRIVATE_KEY"), required=not os.getenv("PRIVATE_KEY"))
    args = parser.parse_args()
    from solcx import compile_source, install_solc
    from web3 import Web3
    install_solc("0.8.20")
    source = Path(__file__).parents[1] / "src/chain/contracts/FaceVerificationRegistry.sol"
    compiled = compile_source(source.read_text(), solc_version="0.8.20")["<stdin>:FaceVerificationRegistry"]
    w3 = Web3(Web3.HTTPProvider(args.rpc_url))
    account = w3.eth.account.from_key(args.private_key)
    contract = w3.eth.contract(abi=compiled["abi"], bytecode=compiled["bin"])
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contract.constructor().build_transaction({"from": account.address, "nonce": nonce, "chainId": w3.eth.chain_id, "gas": 2000000, "maxFeePerGas": w3.to_wei(30, "gwei"), "maxPriorityFeePerGas": w3.to_wei(1, "gwei")})
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(json.dumps({"contractAddress": receipt.contractAddress, "txHash": tx_hash.hex(), "chainId": w3.eth.chain_id}, indent=2))


if __name__ == "__main__":
    main()
