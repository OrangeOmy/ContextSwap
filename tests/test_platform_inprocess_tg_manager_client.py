import asyncio
import unittest

import anyio

from contextswap.platform.services.inprocess_tg_manager_client import InProcessTgManagerClient


class _LoopBoundTelegramService:
    def __init__(self, expected_loop: asyncio.AbstractEventLoop) -> None:
        self.expected_loop = expected_loop

    async def create_topic(self, *, chat_id: str, title: str) -> int:
        assert asyncio.get_running_loop() is self.expected_loop
        return 1001

    async def send_message(self, *, chat_id: str, message_thread_id: int, text: str) -> int:
        assert asyncio.get_running_loop() is self.expected_loop
        return 2002

    async def close_topic(self, *, chat_id: str, message_thread_id: int) -> None:
        assert asyncio.get_running_loop() is self.expected_loop


class InProcessTgManagerClientLoopTest(unittest.TestCase):
    def test_create_session_runs_on_host_loop_from_worker_thread(self) -> None:
        async def scenario() -> None:
            expected_loop = asyncio.get_running_loop()
            tg_client = InProcessTgManagerClient(
                sqlite_path=":memory:",
                auth_token="token",
                market_chat_id="-100123456",
                telegram_service=_LoopBoundTelegramService(expected_loop),
            )
            try:
                result = await anyio.to_thread.run_sync(
                    lambda: tg_client.create_session(
                        transaction_id="0xtxhash",
                        buyer_bot_username="buyer_bot",
                        seller_bot_username="seller_bot",
                        initial_prompt="hello",
                    )
                )
                self.assertEqual(result["message_thread_id"], 1001)
                self.assertEqual(result["status"], "running")
            finally:
                tg_client.close()

        anyio.run(scenario)


if __name__ == "__main__":
    unittest.main()
