import hashlib
import json
import os
import time
from pathlib import Path


class LocalChain:
    """Persistent local simulation; one JSON file survives separate CLI invocations."""
    def __init__(self, path: Path):
        self.path = path
        self.data = json.loads(path.read_text()) if path.exists() else {"records": {}}

    def store(self, fingerprint, url):
        if fingerprint in self.data["records"]:
            raise RuntimeError("record already exists")
        timestamp = int(time.time())
        tx = "0x" + hashlib.sha256(f"{fingerprint}:{url}:{timestamp}".encode()).hexdigest()
        self.data["records"][fingerprint] = {"fingerprint": fingerprint, "url": url, "timestamp": timestamp, "txHash": tx, "blockNumber": len(self.data["records"]) + 1, "network": "local"}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        return self.data["records"][fingerprint]

    def get(self, fingerprint):
        return self.data["records"].get(fingerprint)

class SepoliaChain:
    ABI = [
        {"inputs": [{"internalType": "bytes32", "name": "fp", "type": "bytes32"}, {"internalType": "string", "name": "url", "type": "string"}], "name": "storeRecord", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"internalType": "bytes32", "name": "fp", "type": "bytes32"}], "name": "getRecord", "outputs": [{"internalType": "bytes32", "name": "fingerprint", "type": "bytes32"}, {"internalType": "address", "name": "submitter", "type": "address"}, {"internalType": "uint64", "name": "timestamp", "type": "uint64"}, {"internalType": "string", "name": "matchedUrl", "type": "string"}], "stateMutability": "view", "type": "function"}
    ]

    def __init__(self, address=None):
        try:
            from web3 import Web3
        except ImportError as exc:
            raise RuntimeError("Sepolia requires web3 and eth-account") from exc
        self.w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL"), request_kwargs={"timeout": 20}))
        self.account = self.w3.eth.account.from_key(os.environ["PRIVATE_KEY"])
        self.address = self.w3.to_checksum_address(address or os.environ["CONTRACT_ADDRESS"])
        self.contract = self.w3.eth.contract(address=self.address, abi=self.ABI)

    def store(self, fingerprint, url):
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        tx = self.contract.functions.storeRecord(bytes.fromhex(fingerprint[2:]), url).build_transaction({"from": self.account.address, "nonce": nonce, "chainId": 11155111, "gas": 150000, "maxFeePerGas": self.w3.to_wei(30, "gwei"), "maxPriorityFeePerGas": self.w3.to_wei(1, "gwei")})
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return {"fingerprint": fingerprint, "url": url, "txHash": tx_hash.hex(), "blockNumber": receipt.blockNumber, "gasUsed": receipt.gasUsed, "network": "sepolia", "contractAddress": self.address}

    def get(self, fingerprint):
        record = self.contract.functions.getRecord(bytes.fromhex(fingerprint[2:])).call()
        return {"fingerprint": "0x" + record[0].hex(), "url": record[3], "timestamp": record[2]} if record[2] else None


