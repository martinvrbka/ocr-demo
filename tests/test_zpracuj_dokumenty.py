import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_vytezeni import LocalOpenAICompatibleClient  # noqa: E402
from zpracuj_dokumenty import (  # noqa: E402
    ascii_same_length,
    classify,
    compact,
    extract,
    norm_date,
    plates,
    rule_fakta,
    vins,
)


class TestRuleUtilities(unittest.TestCase):
    def test_ascii_same_length_keeps_length_and_removes_diacritics(self):
        text = "Škoda Ř"
        self.assertEqual(ascii_same_length(text), "Skoda R")
        self.assertEqual(len(text), len(ascii_same_length(text)))

    def test_compact_removes_spaces_and_accents(self):
        self.assertEqual(compact("Škoda Octavia 5AB 1234"), "skodaoctavia5ab1234")

    def test_classify_detects_protokol(self):
        text = (
            "POLICIE ČR PROTOKOL O NEHODĚ V SILNIČNÍM PROVOZU "
            "Datum a čas nehody: 21.09.2026 16:45 Zavinění: řidič vozidla B"
        )
        doc_type, _ = classify(text, False)
        self.assertEqual(doc_type, "protokol")

    def test_classify_keeps_document_photo_from_falling_into_foto(self):
        text = "Faktura 2026 1234 AutoServis CZK 12 345,00"
        doc_type, _ = classify(text, True)
        self.assertEqual(doc_type, "faktura")

    def test_plates_and_vins_extraction(self):
        text = "SPZ 5AB 1234, VIN TMBJG7NE8L0123456, druhé vozidlo 2BC 9876"
        self.assertEqual(plates(text), ["5AB 1234", "2BC 9876"])
        self.assertEqual(vins(text), ["TMBJG7NE8L0123456"])

    def test_norm_date_parses_czech_dates(self):
        self.assertEqual(norm_date("21.09.2026"), "21.09.2026")
        self.assertEqual(norm_date("03.10.2026"), "03.10.2026")

    def test_extract_faktura_fields(self):
        text = (
            "Faktura č. 2026100153\n"
            "Dodavatel: AutoServis Kraus s.r.o.\n"
            "Datum vystavení: 05.10.2026\n"
            "Celkem k úhradě: 12 345,00 Kč\n"
            "Odtah vozidla Škoda Octavia"
        )
        result = extract("faktura", text, "Faktura_2026100153.pdf")
        self.assertEqual(result["Číslo faktury"], "2026100153")
        self.assertEqual(result["Dodavatel"], "AutoServis Kraus s.r.o.")
        self.assertEqual(result["Celkem k úhradě"], "12 345,00 Kč")
        self.assertEqual(result["Za co"], "odtah vozidla")

    def test_extract_kalkulace_fields(self):
        text = (
            "KALKULACE OPRAVY VOZIDLA\n"
            "Zakázka: ZK-2026-0871\n"
            "Datum kalkulace: 24.09.2026\n"
            "Celkem s DPH: 49 011,05 Kč"
        )
        result = extract("kalkulace", text, "kalkulace.xlsx")
        self.assertEqual(result["Zakázka"], "ZK-2026-0871")
        self.assertEqual(result["Datum kalkulace"], "24.09.2026")
        self.assertEqual(result["Celkem s DPH"], "49 011,05 Kč")

    def test_rule_fakta_wraps_extracted_values(self):
        facts = {
            "_spz": ["5AB 1234", "2BC 9876"],
            "_vin": ["TMBJG7NE8L0123456"],
            "_pu": ["PU-2026-004217"],
            "Datum nehody": "21.09.2026",
            "Místo nehody": "Brno",
            "Zavinění": "Petr Svoboda",
        }
        translated = rule_fakta("protokol", facts)
        self.assertEqual(translated["cislo_pojistne_udalosti"], "PU-2026-004217")
        self.assertEqual(translated["vin"], "TMBJG7NE8L0123456")
        self.assertEqual(translated["spz_klienta"], "5AB 1234")
        self.assertEqual(translated["spz_druheho_vozidla"], "2BC 9876")
        self.assertEqual(translated["datum_nehody"], "21.09.2026")

    def test_build_vision_messages_contains_base64_image_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "test.jpg"
            file_path.write_bytes(b"fake-jpeg-content")
            messages = LocalOpenAICompatibleClient.build_vision_messages(
                system="Jsi asistent.",
                prompt="Co je na obrázku?",
                image_path=file_path,
            )
            payload = json.dumps(messages, ensure_ascii=False)
            self.assertIn("image_url", payload)
            self.assertIn("data:image/jpeg;base64", payload)
            self.assertIn("Co je na obrázku?", payload)

    def test_local_client_requests_json_response(self):
        client = LocalOpenAICompatibleClient("http://localhost:11434/v1", "llava:latest")
        captured = {}

        def fake_request(payload):
            captured.update(payload)
            return {"choices": [{"message": {"content": "{}"}}]}

        client._request = fake_request
        client.parse(model="llava:latest", messages=[], max_tokens=100, system="Jsi asistent.")
        self.assertEqual(captured["response_format"], {"type": "json_object"})


if __name__ == "__main__":
    unittest.main()
