import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scripts.run_openrouter import Budget, BudgetStop


class BudgetTests(unittest.TestCase):
    def test_concurrent_reservations_share_one_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            budget = Budget(1, Path(directory) / "spend.json")

            def reserve(_):
                try:
                    budget.reserve(0.3)
                    return True
                except BudgetStop:
                    return False

            with ThreadPoolExecutor(max_workers=6) as pool:
                self.assertEqual(sum(pool.map(reserve, range(20))), 3)
            self.assertAlmostEqual(budget.reserved, 0.9)

    def test_reservation_prevents_overcommit(self):
        with tempfile.TemporaryDirectory() as directory:
            budget = Budget(1, Path(directory) / "spend.json")
            budget.reserve(0.8)
            with self.assertRaises(BudgetStop):
                budget.reserve(0.3)
            self.assertAlmostEqual(budget.reserved, 0.8)

    def test_known_cost_releases_unused_reservation(self):
        with tempfile.TemporaryDirectory() as directory:
            budget = Budget(1, Path(directory) / "spend.json")
            budget.reserve(0.8)
            budget.settle(0.8, 0.1, {})
            budget.reserve(0.8)
            self.assertAlmostEqual(budget.charged, 0.1)

    def test_unknown_cost_keeps_reservation(self):
        with tempfile.TemporaryDirectory() as directory:
            budget = Budget(1, Path(directory) / "spend.json")
            budget.reserve(0.8)
            budget.settle(0.8, None, {})
            with self.assertRaises(BudgetStop):
                budget.reserve(0.3)
