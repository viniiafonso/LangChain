import unittest

from src.chatbot.core import normalize_base_url, parse_pressure_input, search_exam_snippets


class MainUtilitiesTest(unittest.TestCase):
    def test_normalize_base_url_adds_v1(self):
        self.assertEqual(normalize_base_url("http://127.0.0.1:1234"), "http://127.0.0.1:1234/v1")

    def test_parse_pressure_input_valid(self):
        parsed = parse_pressure_input("registrar pressão 130/85")
        self.assertEqual(parsed, {"sistolica": 130, "diastolica": 85})

    def test_parse_pressure_input_shorthand(self):
        parsed = parse_pressure_input("registrar pressão 13/8")
        self.assertEqual(parsed, {"sistolica": 130, "diastolica": 80})

    def test_parse_pressure_input_invalid(self):
        parsed = parse_pressure_input("registrar pressão 999/10")
        self.assertIsNone(parsed)

    def test_search_exam_snippets_by_keyword(self):
        exams = {
            "hemograma.pdf": "Hemoglobina 13.2 g/dL e leucócitos dentro da normalidade.",
            "ecg.pdf": "Ritmo sinusal. Sem alterações isquêmicas agudas.",
        }
        snippets = search_exam_snippets(exams, "como está a hemoglobina?")
        self.assertTrue(snippets)
        self.assertIn("hemograma.pdf", snippets[0])


if __name__ == "__main__":
    unittest.main()
