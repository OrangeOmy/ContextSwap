from web3 import Web3

from contextswap.facilitator.base import BaseFacilitator
from contextswap.x402 import CHAIN_ID, NETWORK_ID


class ConfluxFacilitator(BaseFacilitator):
    def __init__(self, rpc_url: str) -> None:
        super().__init__(CHAIN_ID, NETWORK_ID)
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))

    def send_raw_transaction(self, raw_hex: str) -> str:
        raw_hex = raw_hex.lower()
        if raw_hex.startswith("0x"):
            raw_hex = raw_hex[2:]
        tx_hash = self.web3.eth.send_raw_transaction(bytes.fromhex(raw_hex))
        return tx_hash.hex()
