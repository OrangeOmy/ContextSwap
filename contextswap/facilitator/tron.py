import json
from typing import Any, Dict

import requests
from eth_utils import to_checksum_address

from contextswap.facilitator.base import BaseFacilitator
from contextswap.tron_utils import extract_transfer_contract, tron_hex_to_evm
from contextswap.x402_tron import CHAIN_ID, NETWORK_ID


class TronFacilitator(BaseFacilitator):
    def __init__(self, rpc_url: str, api_key: str | None = None) -> None:
        super().__init__(CHAIN_ID, NETWORK_ID)
        self.rpc_url = rpc_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["TRON-PRO-API-KEY"] = self.api_key
        return headers

    def _extract_tx(self, payment: Dict[str, Any]) -> Dict[str, Any]:
        tx = payment.get("transaction") or payment.get("rawTransaction")
        if not tx:
            raise ValueError("Missing transaction in payment payload")
        if isinstance(tx, str):
            return json.loads(tx)
        if isinstance(tx, dict):
            return tx
        raise ValueError("Invalid transaction payload")

    def verify_payment(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        accepts = requirements.get("accepts", [])
        if not accepts:
            raise ValueError("Missing payment requirements")

        requirement = accepts[0]
        if requirement.get("network") != NETWORK_ID:
            raise ValueError("Wrong network in requirements")

        tx = self._extract_tx(payment)
        contract = extract_transfer_contract(tx)
        owner_hex = contract.get("owner_address")
        to_hex = contract.get("to_address")
        if not owner_hex or not to_hex:
            raise ValueError("Missing owner/to address in transaction")

        payer = to_checksum_address(tron_hex_to_evm(owner_hex))
        pay_to = to_checksum_address(tron_hex_to_evm(to_hex))
        expected_to = to_checksum_address(requirement["payTo"])
        expected_value = int(requirement["amountWei"])
        amount = int(contract.get("amount", 0))

        if pay_to != expected_to:
            raise ValueError("Payment recipient does not match requirement")
        if amount < expected_value:
            raise ValueError("Payment amount is below requirement")

        expected_payer = payment.get("from")
        if expected_payer and to_checksum_address(expected_payer) != payer:
            raise ValueError("Payment sender does not match requirement")

        return {
            "payer": payer,
            "payTo": pay_to,
            "value": amount,
            "network": NETWORK_ID,
            "scheme": payment.get("scheme", "exact"),
            "verified": True,
        }

    def settle_payment(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> str:
        tx = self._extract_tx(payment)
        resp = requests.post(
            f"{self.rpc_url}/wallet/broadcasttransaction",
            json=tx,
            headers=self._headers(),
            timeout=10,
        )
        if resp.status_code != 200:
            raise RuntimeError(resp.text)
        data = resp.json()
        if not data.get("result", True):
            raise RuntimeError(resp.text)
        return data.get("txid") or data.get("txID") or tx.get("txID", "")

    def send_raw_transaction(self, raw_hex: str) -> str:
        raise NotImplementedError("Tron uses broadcasttransaction with signed tx payload")
