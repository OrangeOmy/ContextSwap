import unittest

from tg_manager.services.telethon_service import (
    TelethonError,
    _ensure_topic_title,
    _extract_thread_id_from_updates,
)


class _StubMsg:
    def __init__(self, mid: int) -> None:
        self.id = mid


class _StubUpd:
    def __init__(self, mid: int) -> None:
        self.message = _StubMsg(mid)


class _StubUpdates:
    def __init__(self, mids: list[int]) -> None:
        self.updates = [_StubUpd(m) for m in mids]


class TestTelethonServiceHelpers(unittest.TestCase):
    def test_ensure_topic_title_truncates_and_validates(self) -> None:
        with self.assertRaises(ValueError):
            _ensure_topic_title("   ")

        self.assertEqual(_ensure_topic_title(" tx:1 "), "tx:1")
        long_title = "a" * 200
        self.assertEqual(len(_ensure_topic_title(long_title)), 128)

    def test_extract_thread_id_from_updates(self) -> None:
        result = _StubUpdates([12, 34])
        self.assertEqual(_extract_thread_id_from_updates(result), 12)

        with self.assertRaises(TelethonError):
            _extract_thread_id_from_updates(_StubUpdates([]))


if __name__ == "__main__":
    unittest.main()

