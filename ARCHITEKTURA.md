# Architektura a princip fungování aplikace

Tento projekt je v podstatě jednoduchý, ale velmi praktický pipeline: dostaneš soubor, musíš z něho vytáhnout informace, rozhodnout, co to je, a dát to do správné kategorie. Je to stejný princip, jaký používají většina dokumentových systémů v praxi — jen zjednodušený a přizpůsobený k pojistným událostem.

Nejde o "magii AI" ani o jeden velký model, který vše zařídí. Jde o to, že se data posouvají krok za krokem přes několik vrstev:

1. načíst soubor,
2. přečíst text,
3. poznat typ dokumentu,
4. vyndat obsah,
5. sjednotit ho,
6. případně doplnit AI,
7. uložit a shrnout.

To je klasická architektura počítačového zpracování dokumentů.

---

## 1) Co je vlastně cíl aplikace?

Představ si, že klient nahraje do složky několik dokumentů:

- fakturu za opravu,
- policejní protokol,
- SMS od druhého účastníka,
- fotku auta,
- lékařskou zprávu.

Aplikace se musí rozhodnout:

- co je to za dokument,
- jaké informace z něj vytáhne,
- kde ho uloží,
- jaké údaje z něj použije do souhrnu pojistné události.

Tedy ne jen "to je PDF" nebo "to je JPG", ale "to je faktura z opravny, částka je X, datum je Y, a to souvisí s událostí".

---

## 2) Jaký je hlavní design?

Aplikace má čtyři vrstvy:

### 2.1 Vstupní vrstva
Složka `klient_upload/` je vstupní brána.

V této složce se objeví nový soubor a aplikace jej zahlédne. V teorii se to nazývá watch-folder nebo polling loop:

- aplikace pravidelně kontroluje složku,
- najde nové soubory,
- zpracuje je,
- přesune do výstupního adresáře.

Tady je klíčové, že aplikace není "připravená na jediný typ dokumentu". Může přijmout PDF, DOCX, XLSX, PNG, JPG, e-mail, HTML nebo text.

### 2.2 Vrstva čtení dokumentu
Tady přichází první logický krok: dostat data z dokumentu do textové formy.

- PDF se čte přes `read_pdf()`
- Word přes `read_docx()`
- Excel přes `read_xlsx()`
- e-mail přes `read_eml()`
- HTML přes `strip_html()`
- obrázek přes OCR

Důležité: různé formáty obsahují data různým způsobem. PDF může být:

- normální text,
- sken,
- obrázek,
- nebo kombinace obojího.

Aplikace musí rozlišit, jakým způsobem je třeba dokument přečíst.

### 2.3 Vrstva rozpoznání typu
Po přečtení dokumentu se rozhoduje: "Co to je?"

To dělá funkce `classify()`. Tato funkce:

- převádí text do normalizované podoby,
- hledá klíčová slova,
- srovnává skóre typu dokumentu,
- vybere nejpravděpodobnější typ.

Příklady:

- `faktura` = "faktura", "dodavatel", "celkem k úhradě", "splatnost"
- `protokol` = "policie", "protokol o nehodě", "datum a čas nehody"
- `foto` = obrázek bez čitelného textu, který není dokument

Toto je klasická detekce typu dokumentu podle klíčů a dat.

### 2.4 Vrstva extrakce dat
Když už víme, co dokument je, hledáme v něm konkrétní informace:

- SPZ,
- VIN,
- částka,
- datum,
- místo nehody,
- jméno účastníka,
- číslo faktury,
- druh poškození.

To dělá `extract()`. V tomto kroku se používají regulární výrazy a pravidla typu:

- „najdi text, který následuje po `Celkem k úhradě`“
- „najdi číslo po `VIN`“
- „najdi datum po `Datum nehody`“

Tady se z volného textu stává strukturovaná data.

---

## 3) Co je OCR a proč je důležité?

OCR = Optical Character Recognition.

Jinými slovy: software převádí obrázek s textem do textu, který může číst počítač.

Příklad:

- máš fotografii faktury,
- OCR přečte: "Faktura č. 2026/011", "Celkem k úhradě: 3 630,00 Kč",
- z těchto údajů pak aplikace vytvoří strukturu.

Bez OCR by bylo nemožné zpracovat:

- fotky faktur,
- skenované PDF,
- naskenované policejní protokoly,
- SMS screenshoty,
- ručně psané dokumenty.

V tomto projektu se OCR používá hlavně v `ocr_image()` a v `read_pdf()` pro skenované PDF.

Důležité ale je: OCR není "všechny obrázky rozpozná správně". Pokud je na fotce pouze auto nebo škoda bez textu, OCR nic nevrátí. A to je naprosto normální.

---

## 4) Proč existuje fallback podle pravidel?

Protože AI není vždy dostupný ani spolehlivý.

V této aplikaci je důležitý koncept fallbacku:

- pokud je k dispozici AI model, použije se pro hlubší posouzení,
- pokud ne, nebo pokud selže, aplikace používá pravidla a OCR.

To je zásadní v reálném systému, protože žádný systém nemá 100% spolehlivost.

Pravidla tedy fungují jako stabilní záloha:

- rozpoznají běžné dokumenty,
- zpracují běžné formáty,
- dokážou pracovat offline,
- nevyžadují žádný API klíč.

To je to, co dělá aplikaci praktickou a robustní.

---

## 5) Jak funguje normalizace dat?

Když `extract()` vrátí data, tak třeba:

- "Číslo faktury"
- "Datum nehody"
- "Celkem k úhradě"
- "SPZ"

jsou v různých formátech a s různými názvy. To je problém, protože aplikace potřebuje ke všem dokumentům přistupovat stejně.

Proto existují funkce:

- `rule_fakta()`
- `rule_naklad()`

Ty přepíší data do jednotného formátu, například:

- `datum_nehody`
- `spz_klienta`
- `cislo_pojistne_udalosti`
- `vin`

Takto se z různých dokumentů dá jednoduše vytvořit jeden souhrn události.

Tento krok je důležitý, protože bez něj by aplikace pracovala jen s "hromadou různých textů" a ne s daty, které lze porovnávat a vyhodnocovat.

---

## 6) Kde vstupuje AI?

AI je v tomto systému "enhancement vrstva".

To znamená: nejprve máme klasický pipeline, a až poté se přidá AI, pokud má smysl.

V [ai_vytezeni.py](ai_vytezeni.py) je definováno schéma dat:

- `Analyza`
- `Fakta`
- `Naklad`
- `Udaj`

AI model dostane instrukci a validní JSON schema. To znamená, že model nevrací volný text, ale strukturu, která se dá přímo zpracovat v kódu.

Představ si to takhle:

- pravidla = "rychlá a spolehlivá první vrstva"
- AI = "chytřejší a kontextovější druhá vrstva"

AI dělá věci jako:

- rozhodnout, jestli je dokument v jiném jazyce,
- dát mu popis,
- posoudit jistotu,
- vyhodnotit kvalitu,
- upozornit na podezřelé údaje,
- analyzovat foto lépe než jednoduchý OCR.

---

## 7) Proč je důležité, že model dostává obrázek jako obrázek?

Tady je zásadní praktická poznámka.

Textový model (`llama3.1`) dokáže číst text. Ale když je na obrázku auto, poškození nebo výměna čelního skla, nevidí to jako "obraz". Vidí jen text, tedy nic, pokud není v obrázku text.

Proto se v aktuální verzi používá i multimodální model (`llava:latest`).

Ten umí:

- dostat obrázek jako vstup,
- vidět scénu,
- odpovědět na otázku typu: "Na obrázku je výměna čelního skla?"

Toto je důležitý rozdíl mezi:

- OCR: přečti text z obrázku,
- vision model: pochop obraz.

A to je přesně to, co máš v praxi v pojistných událostech: fotka auta nebo poškozeného dílu, kdy není žádný text, ale člověk z obrázku ví, co to je.

---

## 8) Jak se vytvoří výstup?

Po zpracování souborů se aplikace postará o HTML souhrn.

Tady se seskládá přehled všech dokumentů:

- typ dokumentu,
- popis,
- důležité údaje,
- upozornění,
- doklady a fotky,
- součet nákladů,
- rozporuplné údaje mezi dokumenty.

V praxi to funguje jako pracovní list pro likvidátora: ne jen "všechny dokumenty v jedné složce", ale "strukturované informace, které lze okamžitě posoudit".

---

## 9) Praktický pohled: co se stane s jedním dokumentem?

Představ si, že klient nahraje soubor `Faktura_2026_001.jpg`.

1. `klient_upload/` dostane nový soubor.
2. loop ho najde.
3. `read_text()` rozpozná, že jde o obrázek.
4. `ocr_image()` přečte text z faktury.
5. `classify()` rozhodne: "Toto je faktura".
6. `extract()` vybere "dodavatel, datum, částka, splatnost".
7. `rule_naklad()` vytvoří strukturu skladu.
8. soubor se přesune do `roztridene/06_Faktury/`.
9. souhrn se aktualizuje o fakturu a její údaje.

Stejný princip funguje i pro policejní protokol, SMS, foto vozidla nebo lékařskou zprávu.

---

## 10) Proč je toto dobrá architektura?

Protože rozděluje práci do logických vrstev:

- vstup,
- čtení,
- klasifikace,
- extrakce,
- normalizace,
- AI,
- report.

To je důležité, protože každá vrstva má jiný úkol a nemusí řešit vše najednou.

Výhody:

- snadnější debugování,
- snadnější testování,
- menší riziko chyb,
- možnost vyměnit jednu vrstvu bez zásahu do ostatních,
- možnost přidat další typ dokumentu nebo další zdroj dat.

To je běžný model v produkčních dokumentových systémech.

---

## 11) Shrnutí v jedné větě

Tento projekt je praktický příklad pipeline systému: načíst dokument, přečíst ho, rozpoznat typ, vyextrahovat data, normalizovat je, případně rozšířit AI a pak z toho vytvořit přehled pro člověka.

Jinými slovy: neřešíme jeden velký problém najednou, ale děláme ho po menších krocích, které se dají testovat a zlepšovat jednotlivě.

To je důvod, proč se podobné systémy používají v reálné praxi: je to přehledné, škálovatelné a robustní.
