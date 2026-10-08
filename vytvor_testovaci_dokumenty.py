"""Vytvoří složku testovaci_dokumenty/ s fiktivními podklady k jedné pojistné události.

Všechny firmy, osoby, čísla a částky jsou smyšlené.
Spuštění:  .venv/bin/python vytvor_testovaci_dokumenty.py
"""
import random
import shutil
from email.message import EmailMessage
from pathlib import Path

from docx import Document
from docx.shared import Pt
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle

OUT = Path(__file__).parent / "testovaci_dokumenty"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
SANS, SANS_B = FONT_DIR / "DejaVuSans.ttf", FONT_DIR / "DejaVuSans-Bold.ttf"
SERIF, MONO = FONT_DIR / "DejaVuSerif.ttf", FONT_DIR / "DejaVuSansMono.ttf"

pdfmetrics.registerFont(TTFont("Sans", str(SANS)))
pdfmetrics.registerFont(TTFont("Sans-B", str(SANS_B)))
pdfmetrics.registerFont(TTFont("Serif", str(SERIF)))

random.seed(42)


# ---------- PDF: faktura z autoservisu (moderní tabulkový styl) ----------
def faktura_autoservis():
    path = OUT / "Faktura_2026100153_AutoServis_Kraus.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm)
    h = ParagraphStyle("h", fontName="Sans-B", fontSize=20, textColor=colors.HexColor("#1F4E79"))
    n = ParagraphStyle("n", fontName="Sans", fontSize=9.5, leading=13)
    b = ParagraphStyle("b", fontName="Sans-B", fontSize=9.5, leading=13)
    story = [
        Paragraph("FAKTURA – DAŇOVÝ DOKLAD", h),
        Paragraph("Číslo faktury: 2026100153", b),
        Spacer(1, 6 * mm),
        Table(
            [
                [Paragraph("<b>Dodavatel</b><br/>AutoServis Kraus s.r.o.<br/>Vídeňská 88, 639 00 Brno<br/>"
                           "IČO: 27654321<br/>DIČ: CZ27654321", n),
                 Paragraph("<b>Odběratel</b><br/>Jan Novák<br/>Lipová 12, 602 00 Brno<br/>"
                           "Plátce: Fiktivní pojišťovna a.s. (přímá úhrada)", n)],
            ],
            colWidths=[87 * mm, 87 * mm],
        ),
        Spacer(1, 4 * mm),
        Paragraph("Datum vystavení: 05.10.2026 &nbsp;&nbsp; Datum zdanitelného plnění: 03.10.2026 "
                  "&nbsp;&nbsp; Datum splatnosti: 19.10.2026", n),
        Paragraph("Variabilní symbol: 2026100153 &nbsp;&nbsp; Bankovní účet: 2400123456/2010", n),
        Paragraph("Vozidlo: Škoda Octavia Combi 2.0 TDI, RZ: 5AB 1234, VIN: TMBJG7NE8L0123456", n),
        Paragraph("Číslo pojistné události: PU-2026-004217", n),
        Spacer(1, 5 * mm),
    ]
    rows = [["Položka", "Množství", "Cena/ks bez DPH", "Celkem bez DPH"],
            ["Přední nárazník – lakovaný díl", "1", "12 450,00", "12 450,00"],
            ["Světlomet LED levý", "1", "14 980,00", "14 980,00"],
            ["Blatník přední levý", "1", "4 320,00", "4 320,00"],
            ["Lakování (materiál)", "1", "3 150,00", "3 150,00"],
            ["Práce – klempíř, lakýrník (9,5 h)", "9,5", "590,00", "5 605,00"]]
    t = Table(rows, colWidths=[78 * mm, 22 * mm, 37 * mm, 37 * mm])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Sans", 9),
        ("FONT", (0, 0), (-1, 0), "Sans-B", 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF3F8")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B0C4DE")),
    ]))
    story += [t, Spacer(1, 5 * mm)]
    sums = Table([["Základ DPH 21 %:", "40 505,00 Kč"], ["DPH 21 %:", "8 506,05 Kč"],
                  ["Celkem k úhradě:", "49 011,05 Kč"]], colWidths=[137 * mm, 37 * mm])
    sums.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Sans", 10),
                              ("FONT", (0, 2), (-1, 2), "Sans-B", 11),
                              ("ALIGN", (0, 0), (-1, -1), "RIGHT")]))
    story += [sums, Spacer(1, 10 * mm), Paragraph("Vystavil: Ing. Pavel Kraus, tel. 543 210 987", n)]
    doc.build(story)


# ---------- PDF: policejní protokol (naskenovaný – PDF obsahuje jen obrázek, žádný text) ----------
def policejni_protokol():
    png = OUT / "_tmp_protokol.png"
    scan_image([
        "**POLICIE ČESKÉ REPUBLIKY",
        "Obvodní oddělení Brno - střed, dopravní inspektorát",
        "**PROTOKOL O NEHODĚ V SILNIČNÍM PROVOZU",
        "Č. j.: KRPB-187342-6/ČJ-2026-060006",
        "Datum a čas nehody: 21.09.2026, 16:45",
        "Místo nehody: Brno, křižovatka ulic Husova a Joštova",
        "Účastník 1: Jan Novák, nar. 12.04.1985,",
        "   vozidlo Škoda Octavia, RZ 5AB 1234",
        "Účastník 2: Petr Svoboda, nar. 03.11.1990,",
        "   vozidlo Volkswagen Golf, RZ 2BC 9876",
        "Popis: Řidič vozidla č. 2 nedal přednost v jízdě zprava",
        "   a narazil do levé přední části vozidla č. 1.",
        "Zranění osob: bez zranění. Alkohol: negativní.",
        "Zavinění: řidič vozidla č. 2 (Petr Svoboda)",
        "Odhad hmotné škody: 60 000 Kč",
        "Sepsal: prap. Martin Dvořák",
    ], png, SERIF, size=28, rotate=0.9, paper=(250, 250, 250))
    Image.open(png).convert("RGB").save(OUT / "scan_policie_protokol.pdf", resolution=150)
    png.unlink()


# ---------- DOCX: záznam o dopravní nehodě (euroformulář přepsaný do Wordu) ----------
def zaznam_o_nehode():
    d = Document()
    st = d.styles["Normal"]
    st.font.name, st.font.size = "Calibri", Pt(11)
    d.add_heading("Společný záznam o dopravní nehodě", 0)
    d.add_paragraph("Datum nehody: 21. 9. 2026   Čas: 16:45")
    d.add_paragraph("Místo: Brno, Husova × Joštova")
    d.add_paragraph("Zranění: NE   Škoda na jiných věcech než vozidlech A a B: NE")
    t = d.add_table(rows=1, cols=3)
    t.style = "Light Grid Accent 1"
    t.rows[0].cells[0].text, t.rows[0].cells[1].text, t.rows[0].cells[2].text = "", "Vozidlo A", "Vozidlo B"
    for row in [("Řidič", "Jan Novák", "Petr Svoboda"),
                ("Telefon", "+420 777 123 456", "+420 603 987 654"),
                ("Vozidlo", "Škoda Octavia Combi", "Volkswagen Golf"),
                ("Registrační značka", "5AB 1234", "2BC 9876"),
                ("Pojistitel", "Fiktivní pojišťovna a.s.", "Smyšlená pojišťovna a.s."),
                ("Číslo pojistné smlouvy", "8801234567", "5512009988"),
                ("Číslo zelené karty", "CZ/123/8801234567", "CZ/456/5512009988"),
                ("Viditelná poškození", "levý přední blatník, nárazník, světlomet", "přední nárazník")]:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = v
    d.add_paragraph()
    d.add_paragraph("Okolnosti: Vozidlo B vjíždělo do křižovatky a nedalo přednost vozidlu A "
                    "přijíždějícímu zprava.")
    d.add_paragraph("Podpisy řidičů: Jan Novák, Petr Svoboda")
    d.save(OUT / "zaznam_nehoda_euroformular.docx")


# ---------- XLSX: kalkulace opravy (tabulka z rozpočtového programu) ----------
def kalkulace():
    wb = Workbook()
    ws = wb.active
    ws.title = "Kalkulace"
    ws["A1"] = "KALKULACE OPRAVY VOZIDLA (odhad škody)"
    ws["A1"].font = Font(bold=True, size=14)
    meta = [("Zakázka:", "ZK-2026-0871"), ("Datum kalkulace:", "24.09.2026"),
            ("Vozidlo:", "Škoda Octavia Combi"), ("SPZ:", "5AB1234"), ("VIN:", "TMBJG7NE8L0123456"),
            ("Pojistná událost:", "PU-2026-004217"), ("Zpracoval:", "AutoServis Kraus s.r.o.")]
    for i, (k, v) in enumerate(meta, start=3):
        ws.cell(i, 1, k).font = Font(bold=True)
        ws.cell(i, 2, v)
    hdr = ["Díl / operace", "Typ", "Hodin", "Cena bez DPH"]
    for j, v in enumerate(hdr, 1):
        c = ws.cell(11, j, v)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="C55A11")
    items = [("Nárazník přední", "díl", None, 12450), ("Světlomet LED L", "díl", None, 14980),
             ("Blatník PL", "díl", None, 4320), ("Lak. materiál", "materiál", None, 3150),
             ("Klempířské práce", "práce", 5.5, 3245), ("Lakýrnické práce", "práce", 4, 2360)]
    for i, row in enumerate(items, start=12):
        for j, v in enumerate(row, 1):
            ws.cell(i, j, v)
    ws.cell(19, 3, "Celkem bez DPH").font = Font(bold=True)
    ws.cell(19, 4, 40505).font = Font(bold=True)
    ws.cell(20, 3, "Celkem s DPH")
    ws.cell(20, 4, 49011.05)
    for col, w in zip("ABCD", (26, 22, 16, 16)):
        ws.column_dimensions[col].width = w
    wb.save(OUT / "kalkulace_opravy.xlsx")


# ---------- EML: hlášení škody od klienta e-mailem ----------
def email_hlaseni():
    m = EmailMessage()
    m["From"] = "Jan Novák <jan.novak@example.cz>"
    m["To"] = "skody@fiktivni-pojistovna.example"
    m["Subject"] = "Hlášení pojistné události – Octavia 5AB 1234"
    m["Date"] = "Mon, 22 Sep 2026 08:12:00 +0200"
    m.set_content(
        "Dobrý den,\n\n"
        "hlásím škodnou událost na mém vozidle Škoda Octavia, SPZ 5AB 1234.\n"
        "Dne 21.9.2026 kolem 16:45 do mě v Brně na křižovatce Husova/Joštova narazil "
        "pan Petr Svoboda (VW Golf, 2BC 9876), který nedal přednost zprava.\n"
        "Byla přivolána policie, sepsali jsme i společný záznam.\n\n"
        "Číslo mé pojistné smlouvy: 8801234567\n"
        "Auto je nepojízdné, bylo odtaženo do servisu AutoServis Kraus, Vídeňská 88.\n"
        "Prosím o zapůjčení náhradního vozidla.\n\n"
        "S pozdravem\nJan Novák\ntel. +420 777 123 456\n"
    )
    (OUT / "Hlaseni skody - email.eml").write_bytes(bytes(m))


# ---------- HTML: faktura za náhradní vozidlo (webová faktura) ----------
def faktura_pujcovna():
    html = """<!doctype html><html lang="cs"><head><meta charset="utf-8"><title>Faktura RENT-55821</title>
<style>body{font-family:Georgia,serif;max-width:700px;margin:40px auto;color:#333}
h1{color:#2E7D32;border-bottom:3px solid #2E7D32}td{padding:4px 10px}.r{text-align:right}</style></head>
<body><h1>Půjčovna MobilCar – faktura</h1>
<p><b>Faktura č. RENT-55821</b><br>Vystaveno: 01.10.2026 · Splatnost: 15.10.2026</p>
<p>MobilCar s.r.o., Křenová 40, Brno · IČO: 29876543<br>Zákazník: Jan Novák, Lipová 12, Brno</p>
<p>Náhradní vozidlo po dobu opravy vozidla RZ 5AB 1234 (pojistná událost PU-2026-004217).</p>
<table><tr><td>Škoda Scala, 22.09.2026 – 03.10.2026 (12 dní × 850 Kč)</td><td class="r">10 200,00 Kč</td></tr>
<tr><td>DPH 21 %</td><td class="r">2 142,00 Kč</td></tr>
<tr><td><b>Celkem k úhradě</b></td><td class="r"><b>12 342,00 Kč</b></td></tr></table>
</body></html>"""
    (OUT / "pujcovna_faktura.html").write_text(html, encoding="utf-8")


# ---------- Obrázky: „naskenované“ dokumenty (text jen jako pixely → OCR) ----------
def scan_image(lines, path, font_path, size=30, rotate=0.8, paper=(246, 243, 235)):
    font = ImageFont.truetype(str(font_path), size)
    W, H = 1400, 120 + len(lines) * int(size * 1.7)
    img = Image.new("RGB", (W, H), paper)
    d = ImageDraw.Draw(img)
    y = 60
    for line in lines:
        bold = line.startswith("**")
        text = line.strip("*")
        f = ImageFont.truetype(str(SANS_B), size + 6) if bold else font
        d.text((70, y), text, fill=(35, 35, 40), font=f)
        y += int(size * 1.7)
    # šum + lehké pootočení, ať to vypadá jako sken
    px = img.load()
    for _ in range(W * H // 60):
        x, yy = random.randrange(W), random.randrange(H)
        g = random.randint(160, 230)
        px[x, yy] = (g, g, g)
    img = img.rotate(rotate, expand=True, fillcolor=(210, 210, 210)).filter(ImageFilter.GaussianBlur(0.6))
    img.save(path, quality=80)


def faktura_odtah():
    scan_image([
        "**ODTAHOVÁ SLUŽBA RYCHLÍK",
        "Hybešova 5, 602 00 Brno   IČO: 08765432",
        "",
        "**PŘÍJMOVÝ DOKLAD / FAKTURA č. 0917/2026",
        "Datum vystavení: 21.09.2026",
        "Odběratel: Jan Novák, Lipová 12, Brno",
        "Odtah vozidla Škoda Octavia, SPZ 5AB 1234",
        "Trasa: Husova, Brno -> Vídeňská 88, Brno (8 km)",
        "Odtah osobního vozidla ........ 2 500,00 Kč",
        "Příplatek víkend/svátek ........ 500,00 Kč",
        "DPH 21 % ......................... 630,00 Kč",
        "**Celkem k úhradě: 3 630,00 Kč",
        "Zaplaceno hotově.",
    ], OUT / "IMG_20260921_odtah_uctenka.jpg", MONO, size=28, rotate=-1.2)


def technicky_prukaz():
    scan_image([
        "**OSVĚDČENÍ O REGISTRACI VOZIDLA – ČÁST I",
        "Česká republika",
        "A. Registrační značka: 5AB 1234",
        "B. Datum první registrace: 14.02.2020",
        "C.1 Provozovatel: NOVÁK JAN, LIPOVÁ 12, BRNO",
        "D.1 Tovární značka: ŠKODA",
        "D.3 Obchodní označení: OCTAVIA COMBI",
        "E. Identifikační číslo vozidla (VIN): TMBJG7NE8L0123456",
        "P.1 Zdvihový objem: 1968 cm3   P.3 Palivo: NM",
        "Číslo osvědčení: UAZ 123456",
    ], OUT / "technicak_sken.png", SANS, size=30, rotate=0.6, paper=(225, 238, 228))


# ---------- Obrázky: fotky poškození (žádný text) ----------
def foto_poskozeni(path, seed, sky):
    rnd = random.Random(seed)
    W, H = 1280, 860
    img = Image.new("RGB", (W, H), sky)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H * 0.62, W, H], fill=(95, 95, 100))            # silnice
    d.rounded_rectangle([170, 330, 1110, 610], 60, fill=(150, 20, 30))  # karoserie
    d.polygon([(340, 330), (460, 200), (850, 200), (980, 330)], fill=(140, 18, 28))
    d.polygon([(380, 320), (480, 220), (640, 220), (640, 320)], fill=(170, 200, 220))
    d.polygon([(660, 320), (660, 220), (830, 220), (930, 320)], fill=(170, 200, 220))
    for cx in (330, 950):
        d.ellipse([cx - 95, 520, cx + 95, 710], fill=(25, 25, 25))
        d.ellipse([cx - 45, 570, cx + 45, 660], fill=(170, 170, 170))
    # promáčklina a škrábance vlevo vpředu
    d.polygon([(170, 400), (300, 380), (330, 470), (240, 560), (175, 520)], fill=(90, 15, 20))
    for _ in range(25):
        x, y = rnd.randint(180, 340), rnd.randint(390, 560)
        d.line([x, y, x + rnd.randint(-40, 40), y + rnd.randint(-15, 15)], fill=(220, 210, 210), width=2)
    d.ellipse([180, 420, 260, 470], fill=(60, 60, 60))  # rozbitý světlomet
    img = img.filter(ImageFilter.GaussianBlur(1.2))
    px = img.load()
    for _ in range(W * H // 25):
        x, y = rnd.randrange(W), rnd.randrange(H)
        r, g, b = px[x, y]
        k = rnd.randint(-18, 18)
        px[x, y] = (max(0, min(255, r + k)), max(0, min(255, g + k)), max(0, min(255, b + k)))
    img.save(path, quality=85)


# ---------- Dokument, který k nehodě nepatří ----------
def nesouvisejici():
    (OUT / "poznamky.txt").write_text(
        "Nákupní seznam na víkend:\n- mléko\n- chleba\n- 6 vajec\n- rajčata\n"
        "Nezapomenout vyzvednout děti z kroužku ve čtvrtek.\n", encoding="utf-8")


# =====================================================================================
# NÁROČNÉ DOKUMENTY – jak to chodí v praxi: vyfoceno mobilem, ručně psané, cizí jazyk,
# otočený sken, screenshot zprávy. Ukládají se do testovaci_dokumenty_narocne/.
# =====================================================================================
HARD = Path(__file__).parent / "testovaci_dokumenty_narocne"
HAND = Path("/usr/share/fonts/opentype/urw-base35/Z003-MediumItalic.otf")  # „ručně psané“ písmo


def _paper(lines, size=(1240, 1754), font=SANS, fsize=30, color=(30, 30, 35), bg=(252, 252, 250), x=90, y=110,
           gap=1.75):
    img = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(img)
    for line in lines:
        bold = line.startswith("**")
        f = ImageFont.truetype(str(SANS_B if bold else font), fsize + (8 if bold else 0))
        d.text((x, y), line.strip("*"), fill=color, font=f)
        y += int(fsize * gap)
    return img


def _perspective_coeffs(dst, src):
    import numpy as np
    rows = []
    for (x, y), (u, v) in zip(dst, src):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    return np.linalg.solve(np.array(rows, float), np.array(src, float).reshape(8)).tolist()


def _photo_on_table(paper: Image.Image, path: Path, corners, seed=7):
    """Papír vyfocený mobilem: dřevěný stůl, šikmý úhel, stín, neostrost, JPEG komprese."""
    rnd = random.Random(seed)
    W, H = 1600, 1200
    table = Image.new("RGB", (W, H), (128, 86, 52))
    d = ImageDraw.Draw(table)
    for y in range(0, H, 3):  # léta dřeva
        c = 110 + int(25 * abs(((y * 7919) % 97) / 97 - 0.5)) + rnd.randint(-6, 6)
        d.line([(0, y), (W, y + rnd.randint(-20, 20))], fill=(c + 20, int(c * 0.68), int(c * 0.42)), width=3)
    pw, ph = paper.size
    coeffs = _perspective_coeffs(corners, [(0, 0), (pw, 0), (pw, ph), (0, ph)])
    warped = paper.convert("RGBA").transform((W, H), Image.PERSPECTIVE, coeffs, Image.BICUBIC,
                                             fillcolor=(0, 0, 0, 0))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).polygon([(x + 18, y + 22) for x, y in corners], fill=(0, 0, 0, 110))
    table = Image.alpha_composite(table.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(18)))
    table = Image.alpha_composite(table, warped)
    # nerovnoměrné světlo: stín ruky/telefonu přes roh
    light = Image.new("L", (W, H), 0)
    ImageDraw.Draw(light).ellipse([-500, 500, 700, 1700], fill=90)
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    dark.putalpha(light.filter(ImageFilter.GaussianBlur(120)))
    table = Image.alpha_composite(table, dark).convert("RGB").filter(ImageFilter.GaussianBlur(1.1))
    table.save(path, quality=68)


def narocne_faktura_foto():
    paper = _paper([
        "**AUTOSKLO HORÁK",
        "Cejl 61, 602 00 Brno · IČ 05544332 · neplátce DPH",
        "",
        "Doklad č.:  AH-2026-311",
        "Datum:  25. září 2026",
        "",
        "Zákazník:  p. Novák (tel. 777 123 456)",
        "Vůz:  Octavia kombi, SPZ 5AB-1234",
        "",
        "Výměna čelního skla vč. lepení ......  7 650,-",
        "Kalibrace kamery asistentů ...........    800,-",
        "",
        "**K ÚHRADĚ:  8 450,- Kč",
        "Uhrazeno platební kartou.",
        "",
        "Děkujeme a přejeme šťastnou cestu!",
    ], fsize=34)
    _photo_on_table(paper, HARD / "20260925_183305.jpg", [(330, 95), (1290, 190), (1210, 1150), (210, 1060)])


def narocne_rucni_doklad():
    img = Image.new("RGB", (1300, 820), (248, 246, 236))
    d = ImageDraw.Draw(img)
    for y in range(120, 820, 52):  # linkovaný papír z bločku
        d.line([(0, y), (1300, y)], fill=(170, 200, 230), width=2)
    d.line([(110, 0), (110, 820)], fill=(225, 140, 140), width=2)
    head = ImageFont.truetype(str(SANS_B), 30)
    d.text((140, 40), "PŘÍJMOVÝ POKLADNÍ DOKLAD  č. 47", fill=(40, 40, 40), font=head)
    hand = ImageFont.truetype(str(HAND), 46)
    blue = (25, 45, 140)
    for i, line in enumerate([
        "Přijato od:  Jan Novák, Lipová 12, Brno",
        "Částka:  1 200,- Kč   (slovy tisícdvěstě)",
        "Účel:  úschova havarovaného vozu Octavia 5AB 1234",
        "na hlídaném parkovišti 21.9. – 24.9.2026 (3 noci)",
        "Dne 24. 9. 2026        Přijal:  J. Krejčí",
        "Parkoviště Zábrdovice, Brno",
    ]):
        d.text((140 + random.randint(-6, 6), 128 + i * 104 + random.randint(-5, 5)), line, fill=blue, font=hand)
    d.ellipse([930, 600, 1180, 790], outline=(120, 60, 160), width=5)  # razítko
    d.text((965, 675), "PARKOVIŠTĚ", fill=(120, 60, 160), font=ImageFont.truetype(str(SANS_B), 26))
    img = img.rotate(-3.5, expand=True, fillcolor=(60, 60, 60)).filter(ImageFilter.GaussianBlur(0.8))
    img.save(HARD / "uctenka parkoviste.jpg", quality=72)


def narocne_nemecka_faktura():
    path = HARD / "Rechnung_2026-0451.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    s = ParagraphStyle("s", fontName="Serif", fontSize=10, leading=14)
    h = ParagraphStyle("h", fontName="Sans-B", fontSize=16, alignment=2)
    t = Table([["Pos.", "Bezeichnung", "Menge", "Betrag"],
               ["1", "LED-Scheinwerfer links, Skoda Octavia IV (Original)", "1", "489,00 €"],
               ["2", "Versand nach Tschechien (Express)", "1", "35,00 €"],
               ["", "Zwischensumme netto", "", "524,00 €"],
               ["", "USt. 0 % (innergemeinschaftliche Lieferung)", "", "0,00 €"],
               ["", "Gesamtbetrag", "", "524,00 €"]], colWidths=[12 * mm, 105 * mm, 18 * mm, 30 * mm])
    t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Serif", 9.5), ("FONT", (0, 0), (-1, 0), "Sans-B", 9.5),
                           ("FONT", (0, -1), (-1, -1), "Sans-B", 10), ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
                           ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black), ("ALIGN", (2, 0), (-1, -1), "RIGHT")]))
    doc.build([
        Paragraph("RECHNUNG", h),
        Paragraph("Autoteile Huber GmbH · Landstraße 120 · 4020 Linz · Österreich · UID ATU12345678", s),
        Spacer(1, 6 * mm),
        Paragraph("An: AutoServis Kraus s.r.o., Vídeňská 88, 639 00 Brno, Tschechien (DIČ CZ27654321)", s),
        Paragraph("Rechnungsnummer: 2026-0451 &nbsp;&nbsp; Rechnungsdatum: 29.09.2026 &nbsp;&nbsp; "
                  "Zahlbar bis: 13.10.2026", s),
        Paragraph("Ihre Bestellung: Kunde Novák, Fahrzeug FIN TMBJG7NE8L0123456", s),
        Spacer(1, 6 * mm), t, Spacer(1, 8 * mm),
        Paragraph("Bankverbindung: IBAN AT12 3456 7890 1234 5678 · Vielen Dank für Ihren Auftrag!", s),
    ])


def narocne_lekarska_zprava():
    paper = _paper([
        "MUDr. Eva Malá – praktický lékař, Údolní 15, Brno",
        "",
        "**AMBULANTNÍ ZPRÁVA",
        "Pacient: Novák Jan, nar. 12.4.1985, pojišťovna 111",
        "Datum vyšetření: 22.09.2026",
        "",
        "Pacient udává, že 21.9. byl účastníkem dopravní nehody",
        "(náraz do boku vozidla). Večer začal pociťovat bolest",
        "krční páteře, omezená hybnost hlavy.",
        "",
        "Dg.: S13.4 – distorze krční páteře",
        "Th.: měkký límec 7 dní, analgetika, klidový režim",
        "Pracovní neschopnost od 22.09.2026.",
        "Kontrola za 7 dní.",
    ], font=MONO, fsize=28, bg=(250, 247, 232), gap=1.6)
    # otočeno bokem a zašedlé – jak to vyleze z kancelářského skeneru
    paper = paper.convert("L").rotate(90, expand=True).filter(ImageFilter.GaussianBlur(0.9))
    px = paper.load()
    for _ in range(paper.size[0] * paper.size[1] // 40):
        px[random.randrange(paper.size[0]), random.randrange(paper.size[1])] = random.randint(120, 200)
    paper.save(HARD / "scan0003.jpg", quality=60)


def narocne_sms_screenshot():
    W, H = 720, 1480
    img = Image.new("RGB", (W, H), (236, 229, 221))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 150], fill=(7, 94, 84))
    d.text((40, 70), "Petr Svoboda – Golf", fill="white", font=ImageFont.truetype(str(SANS_B), 34))
    f = ImageFont.truetype(str(SANS), 27)
    bubbles = [
        ("in", "Dobrý den pane Novák, tady Svoboda z té\nnehody na Husově. Ještě jednou se\nomlouvám, byla to moje chyba."),
        ("in", "Škodu jsem nahlásil u Smyšlené pojišťovny,\nčíslo škodní události u nich je\n26-55-0091. Ať to tam vaše pojišťovna\nuvede."),
        ("out", "Dobrý den, děkuji. Předám to.\nAuto je v servisu, oprava cca 2 týdny."),
        ("in", "Kdyby něco, volejte 603 987 654."),
    ]
    y = 200
    for side, text in bubbles:
        tw = max(d.textlength(l, font=f) for l in text.split("\n"))
        th = 40 * len(text.split("\n"))
        x = 30 if side == "in" else W - tw - 70
        d.rounded_rectangle([x, y, x + tw + 40, y + th + 30], 18,
                            fill=(255, 255, 255) if side == "in" else (220, 248, 198))
        d.multiline_text((x + 20, y + 15), text, fill=(20, 20, 20), font=f, spacing=13)
        y += th + 60
    img.save(HARD / "Screenshot_20260923-091544.png")


def narocne():
    shutil.rmtree(HARD, ignore_errors=True)
    HARD.mkdir()
    narocne_faktura_foto()
    narocne_rucni_doklad()
    narocne_nemecka_faktura()
    narocne_lekarska_zprava()
    narocne_sms_screenshot()


# ---------- Další testovací sady (3–4 další sklady) ----------
def _make_eml(path: Path, subject: str, spz: str, vin: str, datum: str, misto: str, vinik: str):
    msg = EmailMessage()
    msg["From"] = "Klient <klient@example.cz>"
    msg["To"] = "skody@pojistovna.example"
    msg["Subject"] = subject
    msg["Date"] = "Tue, 12 Oct 2026 09:15:00 +0200"
    msg.set_content(
        f"Dobrý den,\n\n"
        f"hlásím pojistnou událost na vozidle {spz} (VIN {vin}).\n"
        f"K nehodě došlo {datum} v {misto}.\n"
        f"Při nehodě byl zapojen řidič {vinik}.\n"
        "Vozidlo je poškozené, žádám o posouzení opravy.\n\n"
        "S pozdravem\nJan Novák\n"
    )
    path.write_bytes(bytes(msg))


def _make_protocol_pdf(path: Path, lines: list[str]):
    png = path.with_suffix(".tmp.png")
    scan_image(lines, png, SERIF, size=28, rotate=0.2, paper=(240, 245, 240))
    Image.open(png).convert("RGB").save(path, resolution=150)
    png.unlink()


def _make_invoice_pdf(path: Path, title: str, rows: list[tuple[str, str]], total: str):
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm)
    s = ParagraphStyle("s", fontName="Sans", fontSize=10, leading=14)
    b = ParagraphStyle("b", fontName="Sans-B", fontSize=10, leading=14)
    story = [Paragraph(title, ParagraphStyle("h", fontName="Sans-B", fontSize=18, textColor=colors.HexColor("#1F4E79"))), Spacer(1, 6 * mm)]
    table_rows = [[Paragraph("Položka", b), Paragraph("Částka", b)]]
    table_rows.extend([[Paragraph(item, s), Paragraph(value, s)] for item, value in rows])
    table_rows.append([Paragraph("Celkem k úhradě", b), Paragraph(total, b)])
    table = Table(table_rows, colWidths=[120 * mm, 42 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B0C4DE")),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))
    story.append(table)
    doc.build(story)


def _make_xlsx(path: Path, cnt: str, spz: str, vin: str):
    wb = Workbook()
    ws = wb.active
    ws.title = "Kalkulace"
    ws["A1"] = "KALKULACE OPRAVY"
    ws["A1"].font = Font(bold=True, size=14)
    rows = [
        ("Pojistná událost", cnt),
        ("Vozidlo", "Škoda Octavia"),
        ("SPZ", spz),
        ("VIN", vin),
        ("Položka", "Cena bez DPH"),
        ("Nárazník levý", "12 450 Kč"),
        ("Světlomet", "14 980 Kč"),
        ("Lakování", "3 150 Kč"),
        ("Práce", "6 200 Kč"),
        ("Celkem", "36 780 Kč"),
    ]
    for r, row in enumerate(rows, start=3):
        ws.cell(r, 1, row[0])
        ws.cell(r, 2, row[1])
    wb.save(path)


def _scenario_dir(name: str):
    folder = Path(__file__).parent / name
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir()
    return folder


def scenario_01_klasicka_nehoda():
    folder = _scenario_dir("testovaci_dokumenty_01_klasicka_nehoda")
    _make_eml(folder / "hlaseni_skody.eml", "Hlášení škody – Octavia", "5AB 1234", "TMBJG7NE8L0123456", "21.09.2026", "Brno, Husova a Joštova", "Petr Svoboda")
    _make_protocol_pdf(folder / "policejni_protokol.pdf", [
        "PROTOKOL O NEHODĚ V SILNIČNÍM PROVOZU",
        "Datum: 21.09.2026 16:45",
        "Místo: Brno, Husova × Joštova",
        "Vozidlo A: Škoda Octavia, SPZ 5AB 1234",
        "Vozidlo B: VW Golf, SPZ 2BC 9876",
        "Zranění: bez zranění",
        "Zavinění: řidič vozidla B",
    ])
    _make_xlsx(folder / "kalkulace_opravy.xlsx", "PU-2026-004217", "5AB 1234", "TMBJG7NE8L0123456")
    _make_invoice_pdf(folder / "faktura_servis.pdf", "Faktura AutoServis Kraus", [("Přední nárazník", "12 450,00 Kč"), ("Světlomet LED L", "14 980,00 Kč"), ("Lakování", "3 150,00 Kč")], "30 580,00 Kč")
    foto_poskozeni(folder / "foto_auto.jpg", 11, (180, 205, 230))
    return folder


def scenario_02_nehoda_bez_souhlasu():
    folder = _scenario_dir("testovaci_dokumenty_02_nehoda_bez_souhlasu")
    _make_eml(folder / "email_klienta.eml", "Hlášení škody – jiné vozidlo", "5AB 1234", "TMBJG7NE8L0123456", "03.10.2026", "Praha, Křemencova 31", "Jiří Dvořák")
    _make_protocol_pdf(folder / "protokol.pdf", [
        "Záznam o nehodě",
        "Datum: 03.10.2026 09:10",
        "Místo: Praha, Křemencova 31",
        "Vozidlo A: Škoda Octavia, SPZ 5AB 1234",
        "Vozidlo B: Mercedes C, SPZ 7AA 2222",
        "Zavinění: vozidlo B",
        "UPOZORNĚNÍ: VIN v seznamech se neshoduje",
    ])
    (folder / "poznamky.txt").write_text("Mám ještě doplnit pojišťovnu a číslo smlouvy.\nAuto je v servisu v Modřanech.\n", encoding="utf-8")
    _make_invoice_pdf(folder / "faktura_parkoviste.pdf", "Faktura za parkovací službu", [("Úschova vozidla", "1 200,00 Kč"), ("Příplatek", "150,00 Kč")], "1 350,00 Kč")
    foto_poskozeni(folder / "foto_stred.jpg", 21, (190, 210, 240))
    return folder


def scenario_03_zraneni_a_sms():
    folder = _scenario_dir("testovaci_dokumenty_03_zraneni_a_sms")
    _make_eml(folder / "hlasen_skody.eml", "Hlášení škody – zranění", "5AB 1234", "TMBJG7NE8L0123456", "18.11.2026", "Olomouc, Sokolská 8", "Marek Havel")
    _make_protocol_pdf(folder / "policie.pdf", [
        "POLICIE ČR",
        "Datum: 18.11.2026 08:35",
        "Zranění: bez zranění",
        "Vozidlo: Škoda Octavia, SPZ 5AB 1234",
        "Vozidlo druhé strany: Ford Focus, SPZ 3BC 4421",
    ])
    _make_invoice_pdf(folder / "faktura_ambulance.pdf", "Výdaj lékaře", [("Konsultace", "1 200,00 Kč"), ("Fyzioterapie", "2 400,00 Kč")], "3 600,00 Kč")
    _make_protocol_pdf(folder / "lekarska_zprava.pdf", [
        "AMBULANTNÍ ZPRÁVA",
        "Pacient: Novák Jan",
        "Zhodnocení: bolest krční páteře, omezená hybnost",
        "Dg.: distorze krční páteře",
        "Pracovní neschopnost: 7 dní",
    ])
    narocne_sms_screenshot()
    shutil.copy2(HARD / "Screenshot_20260923-091544.png", folder / "sms_screenshot.png")
    return folder


def scenario_04_bez_policie():
    folder = _scenario_dir("testovaci_dokumenty_04_bez_policie")
    _make_eml(folder / "klient_email.eml", "Hlášení škody – bez protokolu", "4AF 9988", "WVWZZZ1JZ3W123456", "29.09.2026", "Brno, Černá pole", "Zdeněk Bláha")
    _make_xlsx(folder / "rozpocet.xlsx", "PU-2026-009184", "4AF 9988", "WVWZZZ1JZ3W123456")
    _make_invoice_pdf(folder / "faktura_za_svetlo.pdf", "Faktura za světlomet", [("Světlomet levý", "5 300,00 Kč"), ("Doprava", "180,00 Kč")], "5 480,00 Kč")
    _make_invoice_pdf(folder / "faktura_za_kalenie.pdf", "Druhá faktura za světlomet", [("Světlomet levý", "5 300,00 Kč"), ("Práce", "390,00 Kč")], "5 690,00 Kč")
    foto_poskozeni(folder / "foto_vozidla.png", 31, (210, 210, 220))
    return folder


def generuj_dalsi_scenare():
    scenarios = [
        scenario_01_klasicka_nehoda(),
        scenario_02_nehoda_bez_souhlasu(),
        scenario_03_zraneni_a_sms(),
        scenario_04_bez_policie(),
    ]
    for scenario in scenarios:
        print(f"  {scenario.name}")
    print(f"Hotovo: {len(scenarios)} další testovací sady")


if __name__ == "__main__":
    narocne()
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir()
    faktura_autoservis()
    policejni_protokol()
    zaznam_o_nehode()
    kalkulace()
    email_hlaseni()
    faktura_pujcovna()
    faktura_odtah()
    technicky_prukaz()
    foto_poskozeni(OUT / "IMG_20260921_164812.jpg", 1, (180, 205, 230))
    foto_poskozeni(OUT / "foto_auto_zepredu.png", 2, (200, 200, 205))
    nesouvisejici()
    for p in sorted(OUT.iterdir()):
        print(f"  {p.name}")
    print(f"Hotovo: {OUT}")
    generuj_dalsi_scenare()
