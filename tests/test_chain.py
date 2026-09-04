from src.chain.client import LocalChain


def test_local_chain_persists(tmp_path):
    path = tmp_path / "chain.json"
    chain = LocalChain(path)
    record = chain.store("0xabc", "https://example.com")
    assert LocalChain(path).get("0xabc")["txHash"] == record["txHash"]
