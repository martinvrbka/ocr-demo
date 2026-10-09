# Insurance event document sorter demo (auto claim)

This app monitors the `klient_upload/` folder. When a client uploads documents, the application does the following for each file:

1. identifies what it is: damage report, accident report, police report, vehicle document, driver's license, insurance policy, calculation, invoice or receipt, medical report, SMS/correspondence, damage photo, or unrelated file,
2. extracts important details: registration plate, VIN, accident date and place, culprit, amounts, document numbers, and more,
3. moves the file to `roztridene/<type>/`,
4. rewrites the summary in one file: `roztridene/SOUHRN_pojistne_udalosti.html`.

## Two recognition modes

| | **Claude (AI)** | **Rules (no AI)** |
|---|---|---|
| When used | API key is configured (via `.env`) | no key is configured |
| How it reads the document | looks at an image or PDF like a human | OCR + keyword matching |
| Photo invoice, handwritten document, rotated scan, foreign language, SMS screenshot | ✔ works | ✘ interpreted as a photo or not recognized |
| Extra features | confidence, readability note, warnings for adjuster (for example: “part may have been invoiced twice”) | – |
| Cost | a few crowns per document | free, runs offline |

If Claude fails for a document (internet outage, API error), the document is still processed by the rule-based fallback.

## Local AI setup without paid API key

This project supports a no-cost local path via Ollama. The startup script automatically ensures the local server is running and the model is available before the app starts.

1. Install Ollama from https://ollama.com.
2. In the project root, keep the provided `.env` values as-is. The file already contains the local backend defaults:
   - `OLLAMA_BASE_URL=http://localhost:11434/v1`
   - `OLLAMA_MODEL=llava:latest`
3. Run the app with:
   - `./spustit.sh`
4. If asked to use the AI backend, the app is configured to prefer the local Ollama endpoint; if it is not available, it falls back to the rule-based mode automatically.

### Why this model is different

The original `llama3.1` text model can read typed text well, but it cannot understand a photo the same way a vision model does. For damage photos, windshield replacement images, or other vehicle scenes, the app now prefers a multimodal model (`llava:latest`) so it can inspect the image itself rather than only OCR text.

### Verified runtime

This was validated in the workspace:
- the local client builds proper base64 image payloads for multimodal requests
- the project test suite passes
- the local multimodal model download is configured through Ollama and the startup script checks for `llava:latest` before launching the app

## Anthropic API (paid option)

If you want to keep the original paid backend instead of Ollama:

1. Sign in at https://console.anthropic.com and top up credit in the **Billing** section.
2. In the **API Keys** section, click **Create Key** and copy the key.
3. In the project folder `pojistne-udalosti-demo`, copy `.env.example` and rename the copy to `.env` if needed.
4. Open `.env` and paste the key after `ANTHROPIC_API_KEY=` with no spaces.
5. Then run `./spustit.sh` again.

Do not share the key with anyone and do not share the `.env` file.

## Try it out

1. Open a terminal in the `pojistne-udalosti-demo` folder and run `./spustit.sh`. Leave the window open.
2. In your file manager, copy files from `testovaci_dokumenty/` and especially `testovaci_dokumenty_narocne/` into `klient_upload/`.
3. The terminal will print what each file is and where it was moved.
4. Open `roztridene/SOUHRN_pojistne_udalosti.html` by double-clicking it. Press F5 in the browser after adding more files.
5. Stop with Ctrl+C in the terminal. Restore the default state with `./vycistit.sh`.

Each startup creates a full console log in `logs/` named `run_<timestamp>_<pid>.log`. It includes startup checks, model output, document processing, warnings, and the final exit code; the same output remains visible in the terminal.

To compare behavior, run the same files once with the paid API and once with the local Ollama route.

## Test data (all content is fictional)

**`testovaci_dokumenty/`**: “clean” documents that the rules can also handle.

| File | Format | What it is |
|---|---|---|
| Faktura_2026100153_AutoServis_Kraus.pdf | PDF with text | repair invoice |
| scan_policie_protokol.pdf | image-only PDF | police accident report |
| zaznam_nehoda_euroformular.docx | Word | common accident report |
| kalkulace_opravy.xlsx | Excel with formulas | repair estimate |
| Hlaseni skody - email.eml | email | damage report from client |
| pujcovna_faktura.html | web page | replacement vehicle invoice |
| IMG_20260921_odtah_uctenka.jpg | scan | tow receipt |
| technicak_sken.png | scan | vehicle registration document (small TP) |
| IMG_20260921_164812.jpg, foto_auto_zepredu.png | image | damage photos |
| poznamky.txt | text | unrelated file (shopping list) |

**`testovaci_dokumenty_narocne/`**: how it looks in real life.

| File | What it is | Why it is difficult |
|---|---|---|
| 20260925_183305.jpg | front windshield invoice | photographed on a mobile phone at an angle, shadow, blurry |
| uctenka parkoviste.jpg | parking receipt for vehicle storage | handwritten, tilted, stamp |
| Rechnung_2026-0451.pdf | headlight invoice from Austria | German, in euros, supplier is a service center |
| scan0003.jpg | medical report | 90° rotated scan, noise; police report says “no injuries” |
| Screenshot_20260923-091544.png | SMS from the other driver | chat screenshot; includes claim number with his insurer |

The difficult documents hide inconsistencies the summary is expected to capture: injuries that the police report says did not happen, and a headlight that may have been invoiced twice.

**Additional mixed-format claim sets**: `testovaci_dokumenty_05_fotky_z_telefonu/` combines a photographed windshield invoice, a scanned police report, vehicle registration, towing PDF, email, estimate, and damage photo. `testovaci_dokumenty_06_faktura_pdf_a_foto/` includes the same German invoice as both PDF and a phone photo. `testovaci_dokumenty_07_otocene_a_zastinene_doklady/` combines a 90-degree scanned protocol, rotated medical and handwritten parking documents, an invoice PDF, email, and damage photo. `testovaci_dokumenty_08_neuplne_a_rozporuplne_podklady/` mixes conflicting vehicle details, a blurred phone invoice, PDF invoice, email, estimate, SMS-like photo, and vehicle damage photo. Phone captures include perspective, shadows, blur, and JPEG compression.

**Random upload-name cases**: `testovaci_dokumenty_09_necitelne_nazvy_a_mobilni_faktury/`, `testovaci_dokumenty_10_jeden_doklad_dve_podoby/`, and `testovaci_dokumenty_11_smes_fotek_a_skenu/` use meaningless upload names such as `sfds66dfs4.jpg`. When the content is recognized, the processor renames the output file to a descriptive name based on its document type and extracted facts; the original upload name remains visible in the report for traceability. Unrecognized documents keep their original name.

## What the summary shows

- **Event overview** built from all documents. Each fact shows which document it came from. If multiple documents mention the same fact, the more trustworthy source takes precedence (police before SMS).
- **Checks**:
  - missing supporting documents,
  - SPZ, VIN, or accident date mismatch across documents,
  - service invoice against estimate,
  - medical report against protocol stating “no injuries”,
  - duplicate uploaded file,
  - hard-to-read document (request a better copy),
  - warnings from Claude.
- **Costs**: all invoices and receipts are totaled separately for each currency.
- **Photos** with damage description and **details for each document**.

## Files

- `zpracuj_dokumenty.py`: folder monitoring, file reading, rules, classification, and summary generation
- `ai_vytezeni.py`: connection to Claude and the list of fields to extract from each document
- `vytvor_testovaci_dokumenty.py`: regenerates the base and difficult documents plus eleven scenario folders
- [ARCHITEKTURA.md](ARCHITEKTURA.md): technical architecture, module responsibilities, data flow, AI routing, state and failure handling
- [understandingprojectfordummies.md](understandingprojectfordummies.md): a plain-language walkthrough of the same process, OCR and AI concepts
