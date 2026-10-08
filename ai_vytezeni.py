"""Rozpoznání a vytěžení dokumentu pomocí Claude (čte obrázky, skeny i PDF přímo – jako člověk).

Použije se, jen když je k dispozici API klíč (proměnná ANTHROPIC_API_KEY nebo soubor .env
ve složce aplikace). Jinak aplikace pracuje s jednoduchými pravidly v zpracuj_dokumenty.py.
"""
import base64
import io
import json
import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

MODEL = "claude-opus-5"
BASE = Path(__file__).parent


def _read_dotenv_value(name: str) -> Optional[str]:
    env = BASE / ".env"
    if not env.exists():
        return None
    for line in env.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == name:
            return value.strip().strip('"').strip("'") or None
    return None


LOCAL_MODEL = os.environ.get("OLLAMA_MODEL") or os.environ.get("OPENAI_MODEL") or _read_dotenv_value("OLLAMA_MODEL") or "llava:latest"
LOCAL_BASE_URL = os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or _read_dotenv_value("OLLAMA_BASE_URL") or _read_dotenv_value("OPENAI_BASE_URL") or "http://localhost:11434/v1"

TYPY = Literal["hlaseni", "zaznam", "protokol", "doklad_vozidla", "ridicsky_prukaz", "pojistna_smlouva",
               "kalkulace", "faktura", "lekarska_zprava", "foto", "korespondence", "jiny_k_udalosti",
               "nesouvisejici"]


class Udaj(BaseModel):
    nazev: str = Field(description="Česky pojmenovaný údaj, např. 'Číslo faktury', 'Diagnóza'")
    hodnota: str = Field(description="Hodnota tak, jak je v dokumentu (s diakritikou)")


class Fakta(BaseModel):
    """Údaje o pojistné události, které se v dokumentu objevují. Co v dokumentu není, je null."""
    cislo_pojistne_udalosti: Optional[str] = None
    klient: Optional[str] = Field(None, description="Poškozený / náš klient (jméno)")
    telefon_klienta: Optional[str] = None
    pojistna_smlouva_klienta: Optional[str] = None
    vozidlo_klienta: Optional[str] = Field(None, description="Značka a model")
    spz_klienta: Optional[str] = Field(None, description="Ve tvaru '5AB 1234'")
    vin: Optional[str] = None
    datum_nehody: Optional[str] = Field(None, description="DD.MM.RRRR")
    cas_nehody: Optional[str] = None
    misto_nehody: Optional[str] = None
    vinik: Optional[str] = None
    druhy_ucastnik: Optional[str] = None
    spz_druheho_vozidla: Optional[str] = None
    pojistitel_druheho: Optional[str] = None
    cislo_skody_u_pojistitele_druheho: Optional[str] = None
    zraneni: Optional[str] = None
    poskozeni_vozidla: Optional[str] = None


class Naklad(BaseModel):
    """Vyplň jen u faktur, účtenek a pokladních dokladů."""
    dodavatel: Optional[str] = None
    cislo_dokladu: Optional[str] = None
    za_co: Optional[str] = Field(None, description="Krátce česky, např. 'odtah vozidla', 'čelní sklo'")
    datum_vystaveni: Optional[str] = None
    splatnost: Optional[str] = None
    castka_celkem: Optional[float] = Field(None, description="Celkem k úhradě vč. DPH, jako číslo")
    mena: Optional[str] = Field(None, description="CZK, EUR, ...")
    uhrazeno: Optional[bool] = None


class Analyza(BaseModel):
    typ: TYPY
    vyfoceny_dokument: bool = False
    popis: str = ""
    jazyk: str = "neznámý"
    jistota: Literal["vysoka", "stredni", "nizka"] = "nizka"
    kvalita: Optional[str] = Field(None, description="Problémy s čitelností (rozmazané, useknuté, "
                                                     "ručně psané nejasné místo...). Jinak null.")
    upozorneni: list[str] = Field(default_factory=list)
    fakta: Fakta = Field(default_factory=Fakta)
    naklad: Optional[Naklad] = None
    udaje: list[Udaj] = Field(default_factory=list)


SYSTEM = """Jsi asistent likvidátora škod z pojištění vozidel v české pojišťovně.
Dostaneš jeden soubor, který klient nahrál k pojistné události. Může to být cokoli: PDF, sken,
dokument vyfocený mobilem (šikmo, se stíny, rozmazaný), ručně psaný doklad, screenshot zprávy,
fotka auta, dokument v cizím jazyce, nebo něco, co k události nepatří.

Typy:
- hlaseni: hlášení škody od klienta (e-mail, formulář)
- zaznam: společný záznam o dopravní nehodě (euroformulář)
- protokol: policejní protokol / úřední záznam
- doklad_vozidla: osvědčení o registraci (malý/velký TP)
- ridicsky_prukaz, pojistna_smlouva (vč. zelené karty)
- kalkulace: kalkulace / odhad / rozpočet opravy
- faktura: faktura, účtenka, paragon, pokladní doklad – cokoli s částkou k úhradě
- lekarska_zprava: lékařská zpráva, neschopenka
- foto: fotografie vozidla, poškození nebo místa nehody (ne vyfocený dokument!)
- korespondence: SMS, chat, dopis s informacemi k události
- jiny_k_udalosti: souvisí s událostí, ale nepatří do typů výše
- nesouvisejici: s pojistnou událostí nesouvisí

Pravidla:
- Vyfocený dokument zařaď podle obsahu (vyfocená faktura = faktura) a nastav vyfoceny_dokument.
- Opisuj jen to, co v dokumentu skutečně je. Nehádej; co tam není, nech null.
- Data piš DD.MM.RRRR, SPZ ve tvaru '5AB 1234', částky jako čísla.
- Do fakta dej jen údaje o nehodě a vozidlech, které z dokumentu plynou.
- Popisky a popis piš česky, i když je dokument v jiném jazyce.
- Pokud je část nečitelná nebo nejistá, napiš to do kvalita a sniž jistotu."""


def load_api_key() -> Optional[str]:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    if os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OPENAI_BASE_URL"):
        return "local"
    env = BASE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "ANTHROPIC_API_KEY" and value.strip():
                return value.strip().strip('"').strip("'")
            if key.strip() in {"OLLAMA_BASE_URL", "OPENAI_BASE_URL"} and value.strip():
                return "local"
    return None


def _image_block(path: Path) -> dict:
    from PIL import Image, ImageOps
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")  # fotky z mobilu mívají rotaci v EXIF
    img.thumbnail((2000, 2000))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.standard_b64encode(buf.getvalue()).decode()}}


def _pdf_block(path: Path) -> dict:
    return {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                           "data": base64.standard_b64encode(path.read_bytes()).decode()}}


class LocalOpenAICompatibleClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = os.environ.get("OPENAI_API_KEY") or "ollama"

    @staticmethod
    def _image_data_url(path: Path) -> str:
        suffix = path.suffix.lower()
        mime = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".gif": "image/gif",
        }.get(suffix, "image/jpeg")
        encoded = base64.standard_b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    @classmethod
    def build_vision_messages(cls, system: str, prompt: str, image_path: Path) -> list:
        return [{
            "role": "system",
            "content": system,
        }, {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": cls._image_data_url(image_path)}},
            ],
        }]

    def supports_vision(self) -> bool:
        name = (self.model or "").lower()
        return any(token in name for token in ("llava", "qwen2.5vl", "qwen2.5-vl", "vision", "pixtral", "minicpm-v"))

    def _request(self, payload: dict):
        import urllib.request
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def parse(self, *, model: str, messages: list, max_tokens: int, system: str, json_mode: bool = True):
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}] + messages,
            "temperature": 0,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        response = self._request(payload)
        text = response["choices"][0]["message"]["content"]
        if isinstance(text, list):
            text = "".join(part.get("text", "") for part in text if isinstance(part, dict))
        return text


class Analyzator:
    def __init__(self, api_key: str):
        self.provider = "anthropic"
        base_url = (
            os.environ.get("OLLAMA_BASE_URL")
            or os.environ.get("OPENAI_BASE_URL")
            or _read_dotenv_value("OLLAMA_BASE_URL")
            or _read_dotenv_value("OPENAI_BASE_URL")
            or LOCAL_BASE_URL
        )
        model = (
            os.environ.get("OLLAMA_MODEL")
            or os.environ.get("OPENAI_MODEL")
            or _read_dotenv_value("OLLAMA_MODEL")
            or _read_dotenv_value("OPENAI_MODEL")
            or LOCAL_MODEL
        )
        # Lokální OpenAI-compatible model (Ollama, LM Studio, apod.) bez placené API
        if api_key == "local" or base_url != LOCAL_BASE_URL and "localhost" in base_url or "127.0.0.1" in base_url:
            self.provider = "local"
            self.local_client = LocalOpenAICompatibleClient(base_url, model)
            self.anthropic = None
            return
        if base_url and ("localhost" in base_url or "127.0.0.1" in base_url):
            self.provider = "local"
            self.local_client = LocalOpenAICompatibleClient(base_url, model)
            self.anthropic = None
            return
        import anthropic
        self.anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key)

    def analyze(self, path: Path, text: str, is_image: bool) -> Analyza:
        """text = text, který aplikace už přečetla (Word, Excel, e-mail...). Obrázky a PDF jdou přímo."""
        if self.provider == "local":
            def compact_schema(value):
                if isinstance(value, dict):
                    return {key: compact_schema(item) for key, item in value.items()
                            if key not in {"title", "description"}}
                if isinstance(value, list):
                    return [compact_schema(item) for item in value]
                return value

            schema = json.dumps(compact_schema(Analyza.model_json_schema()), ensure_ascii=False,
                                separators=(",", ":"))
            if is_image and self.local_client.supports_vision() and path.exists():
                prompt = (
                    f"Obrázek souboru {path.name}. OCR: {text or 'bez čitelného textu'}. "
                    "Napiš jedinou stručnou českou větu o tom, co je na obrázku vidět. "
                    "U auta pojmenuj poškozenou část a její stav, pokud je jasně viditelný. "
                    "Netvrď probíhající výměnu, pokud je vidět jen hotové auto."
                )
                vision_system = "Odpovídej jen jednou věcnou větou. Neopakuj název souboru ani instrukce."
                messages = self.local_client.build_vision_messages(vision_system, prompt, path)
                response_text = self.local_client.parse(
                    model=self.local_client.model,
                    messages=messages[1:],
                    max_tokens=128,
                    system=messages[0]["content"],
                    json_mode=False,
                )
                caption_lines = [line.strip() for line in response_text.splitlines() if line.strip()]
                caption = caption_lines[-1].lstrip("-*0123456789. ").strip().strip('"') if caption_lines else ""
                if not caption:
                    raise ValueError("model nevrátil popis obrázku")
                if caption.lower() in {"stručný popis česky", "strucny popis cesky"}:
                    raise ValueError("model vrátil zástupný text místo popisu obrázku")
                return Analyza(typ="foto", vyfoceny_dokument=False, popis=caption)
            else:
                prompt = (
                    f"Název souboru: {path.name}\n"
                    f"<obsah_souboru>\n{text or 'Soubor byl načten jako obrázek nebo PDF; OCR text chybí.'}\n</obsah_souboru>\n"
                    "Rozpoznej a vytěž tento dokument. Vrať pouze jeden JSON objekt přesně podle tohoto schématu; "
                    "zachovej všechny povinné klíče a datové typy:\n"
                    f"{schema}"
                )
                response_text = self.local_client.parse(
                    model=self.local_client.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2048,
                    system=SYSTEM,
                )
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`\n")
                if cleaned.lower().startswith("json"):
                    cleaned = cleaned[4:].lstrip()
            parsed = json.loads(cleaned)
            if str(parsed.get("popis", "")).strip().lower() in {"stručný popis česky", "strucny popis cesky"}:
                raise ValueError("model vrátil zástupný text místo popisu obrázku")
            if not isinstance(parsed.get("vyfoceny_dokument"), bool):
                parsed["vyfoceny_dokument"] = str(parsed.get("vyfoceny_dokument", "")).lower() in {"true", "yes", "ano", "1"}
            confidence = str(parsed.get("jistota", "nizka")).lower()
            confidence = confidence.translate(str.maketrans("áčďéěíňóřšťúůýž", "acdeeinorstuuyz"))
            parsed["jistota"] = confidence if confidence in {"vysoka", "stredni", "nizka"} else "nizka"
            return Analyza.model_validate(parsed)

        if is_image:
            content = [_image_block(path)]
        elif path.suffix.lower() == ".pdf":
            content = [_pdf_block(path)]
        else:
            content = [{"type": "text", "text": f"<obsah_souboru>\n{text}\n</obsah_souboru>"}]
        content.append({"type": "text", "text": f"Název souboru: {path.name}\nRozpoznej a vytěž tento dokument."})
        response = self.client.messages.parse(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM,
            messages=[{"role": "user", "content": content}],
            output_format=Analyza,
            # Když bezpečnostní filtr požadavek odmítne, API ho samo zkusí na jiném modelu.
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
            extra_body={"fallbacks": "default"},
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            raise RuntimeError(f"model dokument odmítl zpracovat ({response.stop_reason})")
        return response.parsed_output
