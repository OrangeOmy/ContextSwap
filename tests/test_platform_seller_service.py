import unittest

from eth_account import Account

from contextswap.platform.db.engine import connect_sqlite, init_db
from contextswap.platform.services import seller_service


class SellerServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = connect_sqlite(":memory:")
        init_db(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_register_and_search(self) -> None:
        addr = Account.create().address
        seller = seller_service.register_seller(
            self.conn,
            evm_address=addr,
            price_wei=1234,
            price_tron_sun=2000,
            description="test seller",
            keywords=["alpha", "beta"],
            seller_id=None,
        )
        self.assertEqual(seller.status, "active")
        self.assertEqual(seller.price_conflux_wei, 1234)
        self.assertEqual(seller.price_tron_sun, 2000)

        results = seller_service.search_sellers(self.conn, keyword="alpha")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].seller_id, seller.seller_id)

    def test_unregister(self) -> None:
        addr = Account.create().address
        seller = seller_service.register_seller(
            self.conn,
            evm_address=addr,
            price_wei=100,
            description="test seller",
            keywords="gamma",
            seller_id=None,
        )
        inactive = seller_service.unregister_seller(self.conn, seller_id=seller.seller_id)
        self.assertEqual(inactive.status, "inactive")

        results = seller_service.search_sellers(self.conn, keyword="gamma")
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
