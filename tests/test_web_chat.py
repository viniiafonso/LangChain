import unittest

from src.chatbot.web import is_pressure_message, normalize_text, parse_message_payload


class WebChatUtilitiesTest(unittest.TestCase):
    def test_normalize_text_removes_accents(self):
        self.assertEqual(normalize_text("Pressão Arterial"), "pressao arterial")

    def test_is_pressure_message_accepts_accented_text(self):
        self.assertTrue(is_pressure_message("registrar pressão 12/8"))

    def test_parse_message_payload_valid(self):
        payload = {"message": "  Quero ver consultas  "}
        self.assertEqual(parse_message_payload(payload), "Quero ver consultas")

    def test_parse_message_payload_invalid(self):
        self.assertIsNone(parse_message_payload({"message": 123}))


if __name__ == "__main__":
    unittest.main()
