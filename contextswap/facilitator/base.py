from abc import ABC, abstractmethod
from typing import Any, Dict, Protocol

from web3 import Web3

from contextswap.evm import decode_raw_transaction


class FacilitatorClient(Protocol):
    def verify_payment(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def settle_payment(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> str:
        ...


class BaseFacilitator(ABC):
    def __init__(self, chain_id: int, network_id: str) -> None:
        self.chain_id = chain_id
        self.network_id = network_id

    def verify_payment(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        raw_tx = payment.get("rawTransaction")
        if not raw_tx:
            raise ValueError("Missing rawTransaction in payment payload")

        decoded = decode_raw_transaction(raw_tx)

        if decoded.get("chain_id") != self.chain_id:
            raise ValueError("Wrong chain_id in transaction")

        accepts = requirements.get("accepts", [])
        if not accepts:
            raise ValueError("Missing payment requirements")

        requirement = accepts[0]
        expected_to = Web3.to_checksum_address(requirement["payTo"])
        expected_value = int(requirement["amountWei"])

        if decoded["to"] != expected_to:
            raise ValueError("Payment recipient does not match requirement")
        if decoded["value"] < expected_value:
            raise ValueError("Payment amount is below requirement")

        return {
            "payer": decoded["from"],
            "payTo": decoded["to"],
            "value": decoded["value"],
            "network": self.network_id,
            "scheme": payment.get("scheme", "exact"),
        }

    def settle_payment(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> str:
        raw_tx = payment.get("rawTransaction")
        if not raw_tx:
            raise ValueError("Missing rawTransaction in payment payload")
        return self.send_raw_transaction(raw_tx)

    @abstractmethod
    def send_raw_transaction(self, raw_hex: str) -> str:
        raise NotImplementedError
