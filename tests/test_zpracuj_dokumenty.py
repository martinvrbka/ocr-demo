import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_vytezeni import Analyzator, LocalOpenAICompatibleClient  # noqa: E402
from zpracuj_dokumenty import (  # noqa: E402
    ascii_same_length,
    classify,
    compact,
    extract,
    norm_date,
    plates,
    read_pdf,
    rule_fakta,
    vins,
    Zpracovani,
)


class TestRuleUtilities(unittest.TestCase):
    def test_read_pdf_extracts_text_from_fixture(self):
        text, scanned = read_pdf(ROOT / "testovaci_dokumenty" / "Faktura_2026100153_AutoServis_Kraus.pdf")
        self.assertFalse(scanned)
        self.assertIn("FAKTURA", text)

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

    def test_classify_recognizes_medical_correspondence_and_foreign_receipts(self):
        samples = {
            "ambulantni zprava pacient udava bolest pracovni neschopnost": "lekarska_zprava",
            "dobry den pane novak omlouvam se cislo skodni udalosti u nich je 26-55-0091": "korespondence",
            "rechnung rechnungsnummer 2026-0451 betrag 489,00 eur": "faktura",
            "prijmovy pokladni doklad prijato castka 1 200 kc parkoviste": "faktura",
            "doklad vymena celniho skla kuhrade 8 450 kc": "faktura",
        }
        for text, expected in samples.items():
            with self.subTest(expected=expected, text=text):
                self.assertEqual(classify(text, False)[0], expected)

    def test_extracts_amount_and_scope_from_receipt(self):
        text = "Parkoviste Zabrdovice, Brno\nPRIJMOVY POKLADNI DOKLAD\nCastka: 1 200,- Kc\nUcel: uschova vozu na parkovisti\nDne 24.9.2026"
        result = extract("faktura", text, "uctenka.jpg")
        self.assertEqual(result["_castka"], 1200)
        self.assertEqual(result["Dodavatel"], "Parkoviste Zabrdovice")
        self.assertEqual(result["Za co"], "parkování vozidla")
        self.assertEqual(result["Datum vystavení"], "24.09.2026")

    def test_extracts_german_invoice_total_instead_of_line_item_quantity(self):
        text = "RECHNUNGAutoteile Huber GmbH\nBetrag\n1\nLED-Scheinwerfer links\n1\n489,00 \x08\nGesamtbetrag\n524,00 \x01"
        result = extract("faktura", text, "Rechnung_2026-0451.pdf")
        self.assertEqual(result["_castka"], 524)
        self.assertEqual(result["Měna"], "EUR")
        self.assertEqual(result["Dodavatel"], "Autoteile Huber GmbH")
        self.assertEqual(result["Celkem k úhradě"], "524,00 EUR")
        self.assertEqual(result["Za co"], "výměna světlometu")

    def test_extracts_supplier_and_number_from_flattened_photo_invoice(self):
        text = "Doklad.:AH-2026-311 Vymena celniho skla KUHRADE:8450,-Kc AUTOSKLOHORAK"
        result = extract("faktura", text, "20260925_183305.jpg")
        self.assertEqual(result["Číslo faktury"], "AH-2026-311")
        self.assertEqual(result["Dodavatel"], "AUTOSKLOHORAK")

    def test_extracts_windshield_replacement_from_photo_invoice_ocr(self):
        text = "Doklad.:AH-2026-311\nVymena celniho skla ve. lepeni\nKUHRADE:8450,-Kc"
        result = extract("faktura", text, "20260925_183305.jpg")
        self.assertEqual(result["_castka"], 8450)
        self.assertEqual(result["Za co"], "výměna čelního skla")

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

    def test_local_analysis_prompt_includes_the_actual_json_schema(self):
        captured = {}

        class FakeClient:
            model = "llava:latest"

            def supports_vision(self):
                return False

            def parse(self, **kwargs):
                captured.update(kwargs)
                return json.dumps({
                    "typ": "faktura", "vyfoceny_dokument": False, "popis": "Faktura.",
                    "jazyk": "čeština", "jistota": "vysoka", "upozorneni": [],
                    "fakta": {}, "udaje": [],
                })

        analyzer = Analyzator.__new__(Analyzator)
        analyzer.provider = "local"
        analyzer.local_client = FakeClient()
        with tempfile.TemporaryDirectory() as tmp:
            analyzer.analyze(Path(tmp) / "invoice.txt", "Faktura", False)
        prompt = captured["messages"][0]["content"]
        self.assertIn('"properties"', prompt)
        self.assertIn('"vyfoceny_dokument"', prompt)
        self.assertIn('"fakta"', prompt)

    def test_local_vision_error_is_not_retried_as_text(self):
        calls = []

        class FakeClient:
            model = "llava:latest"

            def supports_vision(self):
                return True

            def build_vision_messages(self, system, prompt, image_path):
                return [{"role": "system", "content": system}, {"role": "user", "content": prompt}]

            def parse(self, **kwargs):
                calls.append(kwargs)
                raise TimeoutError("model timeout")

        analyzer = Analyzator.__new__(Analyzator)
        analyzer.provider = "local"
        analyzer.local_client = FakeClient()
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "photo.jpg"
            image_path.write_bytes(b"fake image")
            with self.assertRaises(TimeoutError):
                analyzer.analyze(image_path, "", True)
        self.assertEqual(len(calls), 1)

    def test_local_image_analysis_uses_a_short_caption(self):
        captured = {}

        class FakeClient:
            model = "llava:latest"

            def supports_vision(self):
                return True

            def build_vision_messages(self, system, prompt, image_path):
                captured["prompt"] = prompt
                return [{"role": "system", "content": system}, {"role": "user", "content": prompt}]

            def parse(self, **kwargs):
                captured["max_tokens"] = kwargs["max_tokens"]
                captured["json_mode"] = kwargs["json_mode"]
                return "Instrukce: popiš obrázek.\nSoubor: damage.jpg\nPřední sklo je prasklé."

        analyzer = Analyzator.__new__(Analyzator)
        analyzer.provider = "local"
        analyzer.local_client = FakeClient()
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "damage.jpg"
            image_path.write_bytes(b"fake image")
            result = analyzer.analyze(image_path, "", True)
        self.assertLess(len(captured["prompt"]), 1000)
        self.assertNotIn("stručný popis česky", captured["prompt"])
        self.assertEqual(captured["max_tokens"], 128)
        self.assertFalse(captured["json_mode"])
        self.assertFalse(result.vyfoceny_dokument)
        self.assertEqual(result.jistota, "nizka")
        self.assertEqual(result.popis, "Přední sklo je prasklé.")

    def test_local_ai_is_skipped_for_rule_classified_documents(self):
        class FakeLocalAI:
            provider = "local"

            def analyze(self, *args):
                raise AssertionError("local AI should not run for a clearly classified invoice")

        processor = Zpracovani.__new__(Zpracovani)
        processor.ai = FakeLocalAI()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "invoice.txt"
            output = root / "processed"
            source.write_text("Faktura č. 2026-1234\nDodavatel: Autoservis\nCelkem k úhradě: 1200 Kč",
                              encoding="utf-8")
            with patch("zpracuj_dokumenty.OUT", output):
                result = processor.process(source)
            self.assertEqual(result["typ"], "faktura")
            self.assertEqual(result["zdroj"], "pravidla")
            self.assertEqual(result["naklad"]["castka_celkem"], 1200)


if __name__ == "__main__":
    unittest.main()
