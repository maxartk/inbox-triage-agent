import json
import tempfile
import unittest
from pathlib import Path

from inbox_triage.classifier import classify, extract_order_id
from inbox_triage.drafts import draft_reply
from inbox_triage.outbox import Outbox


class ClassifierTests(unittest.TestCase):
    def test_return_intent_with_order(self):
        result = classify("Vrácení zboží", "Dobrý den, chci vrátit objednávku č. 123456.")
        self.assertEqual(result.intent, "return")
        self.assertEqual(result.order_id, "123456")
        self.assertFalse(result.needs_human)

    def test_order_status_without_number_escalates(self):
        result = classify("Kde je moje zásilka?", "Dobrý den, kdy dorazí balík?")
        self.assertEqual(result.intent, "order_status")
        self.assertTrue(result.needs_human)

    def test_unknown_goes_to_human(self):
        result = classify("Spolupráce", "Nabízíme velkoobchodní ceny.")
        self.assertEqual(result.intent, "other")
        self.assertTrue(result.needs_human)

    def test_ukrainian_message_detected(self):
        result = classify("Замовлення", "Вітаю, де замовлення #778899?")
        self.assertEqual(result.language, "uk")
        self.assertEqual(result.order_id, "778899")

    def test_hash_order_pattern(self):
        self.assertEqual(extract_order_id("objednávka #904211"), "904211")

    def test_urgent_flag(self):
        result = classify("URGENT", "Prosím ihned, reklamace objednávky #555111")
        self.assertTrue(result.urgent)


class DraftTests(unittest.TestCase):
    def test_draft_contains_order_number(self):
        draft = draft_reply("return", "123456")
        self.assertIn("123456", draft["body"])
        self.assertIn("14 dnů", draft["body"])

    def test_unknown_intent_raises(self):
        with self.assertRaises(ValueError):
            draft_reply("other", "1")


class OutboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.outbox = Outbox(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _submit(self, item_id="MSG-1"):
        return self.outbox.submit({"id": item_id, "triage": {"intent": "return"}, "draft": {"subject": "s", "body": "b"}})

    def test_submit_creates_pending(self):
        self._submit()
        pending = self.outbox.list_pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["status"], "pending_approval")

    def test_approve_moves_to_sent_and_audits(self):
        self._submit()
        result = self.outbox.approve("MSG-1", "maksym")
        self.assertEqual(result["status"], "approved")
        self.assertEqual(self.outbox.list_pending(), [])
        audit = self.outbox.read_audit()
        self.assertEqual([r["action"] for r in audit], ["submitted", "approved"])
        self.assertEqual(audit[-1]["actor"], "maksym")

    def test_approve_requires_actor(self):
        self._submit()
        with self.assertRaises(PermissionError):
            self.outbox.approve("MSG-1", "  ")

    def test_second_approve_is_idempotent(self):
        self._submit()
        self.outbox.approve("MSG-1", "maksym")
        again = self.outbox.approve("MSG-1", "maksym")
        self.assertEqual(again["status"], "already_sent")

    def test_reject_writes_reason(self):
        self._submit()
        self.outbox.reject("MSG-1", "maksym", "chybí číslo objednávky")
        audit = self.outbox.read_audit()
        self.assertEqual(audit[-1]["action"], "rejected")
        self.assertEqual(audit[-1]["reason"], "chybí číslo objednávky")


if __name__ == "__main__":
    unittest.main()
