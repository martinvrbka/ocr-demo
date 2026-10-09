# Pochopení projektu úplně od základů

Tenhle dokument je pro člověka, který chce vědět, co aplikace dělá a proč, ale nechce začínat čtením Pythonu. Nejde o příručku k programování. Je to průchod jedním dokumentem od chvíle, kdy ho klient nahraje, až po okamžik, kdy ho najdeš ve správné složce a v HTML souhrnu.

## Nejdřív jednoduchý obraz

Představ si malou podatelnu pojišťovny:

- `klient_upload/` je příchozí přihrádka.
- Aplikace je pracovník, který každou chvíli kontroluje, jestli něco přibylo.
- OCR je čtečka, která z fotky nebo skenu zkouší přečíst písmena.
- Pravidla rozhodují, zda jde o fakturu, protokol, technický průkaz nebo jiný známý typ.
- AI je konzultant pro případy, kdy obyčejná pravidla nestačí, a pro popis fotek.
- `roztridene/` je archiv s uspořádanými soubory.
- `SOUHRN_pojistne_udalosti.html` je přehled pro člověka, který případ kontroluje.

Aplikace tedy není jedno tlačítko, které „magicky chápe všechno“. Je to několik menších kroků. Když jeden krok něco neví, další část procesu se většinou pokusí bezpečně pokračovat.

## Co se stane po spuštění

Spustíš `./spustit.sh`. Skript připraví místní prostředí pro model, založí log běhu a spustí Python aplikaci. Ve výchozím režimu pak aplikace opakovaně kontroluje `klient_upload/`.

Jsou dva režimy:

- `./spustit.sh` nechá aplikaci běžet a čekat na další soubory.
- `./spustit.sh --jednou` zpracuje právě dostupné soubory a skončí.

Při běžném běhu aplikace čeká přibližně sekundu mezi kontrolami. Nezačne číst soubor, který se ještě kopíruje: nejprve zkontroluje jeho velikost a ověří, že se nezměnila.

### Proč může `vycistit.sh` odmítnout práci?

Čištění maže archiv i inbox. Kdyby se to stalo ve chvíli, kdy aplikace ještě běží, její stará paměť by mohla obsahovat informace o souborech, které už byly smazané. Proto `./vycistit.sh` kontroluje zámek aplikace a za běhu odmítne mazat. Nejdřív zastav watcher pomocí `Ctrl+C`, potom teprve čistit.

## Jeden konkrétní příklad

Klient nahraje soubor `sfds66dfs4.jpg`. Název vypadá jako náhodná změť znaků, ale aplikace se nedívá jen na název. Zajímá ji hlavně obsah.

### 1. Aplikace pozná formát

Přípona `.jpg` říká, že jde o obrázek. Sama o sobě ale neříká, jestli je uvnitř faktura, technický průkaz, SMS, nebo jen fotografie auta.

### 2. OCR se pokusí přečíst písmena

OCR znamená „optické rozpoznávání znaků“. Zjednodušeně: vezme pixely obrázku a pokusí se z nich udělat text.

Na fotce faktury může OCR najít například:

```text
AUTO SKLO NOVÁK
Doklad č. ASN-2026-882
Výměna čelního skla
Celkem k úhradě: 10 250 Kč
```

Telefonní fotka může být šikmá, rozmazaná, tmavá nebo otočená. OCR proto může některé znaky přečíst špatně. Třeba `0` zamění za `O`, část řádku přeskočí nebo slepí dvě slova dohromady.

### 3. Pravidla rozhodnou, co dokument je

Aplikace hledá charakteristická slova a počítá jejich skóre. Slova jako „faktura“, „doklad“ a „celkem k úhradě“ ukazují na fakturu. „Policie“, „číslo jednací“ a „zavinění“ zase ukazují na policejní protokol.

To je důvod, proč název `sfds66dfs4.jpg` není překážka: typ se určuje z obsahu, ne z původního názvu souboru.

### 4. Vytáhnou se důležité hodnoty

Když pravidla poznají fakturu, další pravidla se pokusí získat například dodavatele, číslo dokladu, částku, měnu a účel. Tomuto kroku se říká extrakce: z dlouhého textu se vyberou konkrétní údaje.

Například volný text:

```text
Výměna čelního skla ... 9 300 Kč
Celkem k úhradě: 10 250 Kč
```

se uloží také jako strukturovaná data přibližně tohoto tvaru:

```json
{
  "typ": "faktura",
  "za_co": "výměna čelního skla",
  "castka_celkem": 10250,
  "mena": "CZK"
}
```

Díky tomu umí souhrn sčítat částky, aniž by musel znovu hádat z dlouhého textu.

### 5. Původní jméno se může změnit

Když je název zjevně náhodný, například `sfds66dfs4.jpg`, aplikace ho po rozpoznání nahradí popisnějším jménem, například:

```text
06_Faktury/faktura_vymena_celniho_skla_asn_2026_882.jpg
```

Původní název se neztratí. Uloží se do záznamu a zobrazí se v souhrnu, takže je pořád možné dohledat, jak klient soubor skutečně pojmenoval.

Pokud už název dává smysl, například `invoice_AG-2026-449.pdf`, aplikace ho ponechá. Pokud typ vůbec nerozpozná, také název nehádá a ponechá původní.

### 6. Soubor se přesune a uloží

Soubor už nezůstává v `klient_upload/`. Přesune se do příslušné podsložky, například `roztridene/06_Faktury/`. To je důvod, proč se po úspěšném běhu inbox vyprázdní: soubory nejsou jen přečtené, ale archivované.

Vedle souborů aplikace aktualizuje `roztridene/.databaze.json`. To je její strojově čitelný seznam zpracovaných dokumentů a vytěžených údajů.

### 7. Aktualizuje se přehled pro člověka

Nakonec aplikace vytvoří `roztridene/SOUHRN_pojistne_udalosti.html`. V něm uvidíš dokumenty, vytěžené údaje, náklady, fotky a upozornění. HTML otevřeš v prohlížeči.

## OCR a AI nejsou totéž

Tohle je jeden z nejdůležitějších rozdílů v projektu:

### OCR čte text

OCR pomáhá přečíst písmo z fotky faktury, skenu policejního protokolu nebo screenshotu SMS. Neumí ale spolehlivě rozhodnout, co je na obyčejné fotce auta.

### Vision model se dívá na obraz

Vision model, v tomto projektu místní `llava:latest`, dostane samotný obrázek a může stručně popsat, co je vidět. To se používá zejména u nejednoznačných fotografií.

### Co AI po přečtení obrázku vrátí?

Je dobré rozlišit dvě věci:

- OCR vrací rozpoznaný text, například řetězec „Celkem k úhradě 10 250 Kč“.
- Pravidla nebo AI potom text převádějí do společné struktury, například `Naklad.castka_celkem = 10250` a `Naklad.mena = "CZK"`.

Takže přesnější požadavek není „AI ať vrátí stejné OCR“. Je to: **když OCR selže, ať AI vrátí stejné strukturované údaje, které z OCR normálně vytváří zbytek aplikace**. Díky tomu mohou obě cesty krmit stejný souhrn.

### Jak se to chová dnes

1. Python nejdřív zavolá OCR a pravidlovou klasifikaci.
2. Pokud OCR a pravidla poznají typ, například fakturu, místní AI se přeskočí. V současném kódu se neověřuje, jestli OCR vytáhlo i všechna důležitá pole. Faktura tedy může být označená jako faktura, i když kvůli stínu chybí částka.
3. Pokud výsledek zůstane „neznámý“ nebo „foto“, místní vision model dostane obrázek a vrací krátký popis jednou větou.
4. Tento popis není OCR přepis a neobsahuje automaticky číslo faktury, částku, VIN ani jiné vytěžené hodnoty.

Proto tvůj příklad se stínem na faktuře odhaluje skutečnou mezeru: OCR může najít slovo „faktura“, klasifikátor dokument zařadí správně, ale částku nepřečte. Protože typ už je známý, AI se dnes vůbec nezeptá.

### Jak by měl vypadat zpětný pokus přes AI

Doporučený tok je „OCR napřed, AI jako oprava chybějících částí“:

1. OCR přečte, co dokáže, a uloží svůj text i případnou jistotu jednotlivých řádků.
2. Pravidla zkusí určit typ a vytěžit údaje.
3. Aplikace zkontroluje nejen typ dokumentu, ale také jeho důležitá pole. U faktury například částku a měnu; u technického průkazu SPZ a VIN; u protokolu datum a účastníky.
4. Pokud OCR není dost jisté nebo některá důležitá pole chybí, aplikace pošle **původní obrázek a částečný OCR text** vision modelu.
5. Model vrátí stejnou strukturu `Analyza` jako ostatní cesta: typ, fakta, náklad a další údaje. Částka bude číslo, měna třeba `CZK` a neznámá hodnota zůstane prázdná, ne vymyšlená.
6. Aplikace ověří výsledek, pole po poli ho sloučí s OCR a pravidly a uloží ho do stávající databáze a souhrnu.

Příklad: OCR našlo dodavatele a číslo dokladu, ale ne částku. AI z fotky doplní částku `10250` a měnu `CZK`. Původní OCR text nezmizí; zůstane jako zdroj a při sporu se hodnoty nevyberou potichu. Vytvoří se upozornění „OCR uvádí X, vizuální rozbor Y – ověřit“.

Tohle není nekonečná smyčka, ve které se OCR a AI opakovaně přetahují. Je to jeden řízený druhý pokus s jasným limitem. Když model selže nebo vyprší čas, aplikace zachová OCR výsledek, označí chybějící pole a pokračuje.

Placená Anthropic větev už umí vracet strukturovanou analýzu. V místní větvi `llava:latest` dnes vision cesta vrací pouze krátký popis; strukturované doplnění OCR polí je doporučené rozšíření, ne současná funkce. Souhrn ukazuje zdroj zpracování, takže při zkoušení poznáš, která cesta se použila.

### Pravidla jsou rychlá první vrstva

Když OCR přečte známý dokument a pravidla ho dokážou zařadit, místní AI se obvykle přeskočí. Proto mohou běžné faktury a protokoly projít rychle: model nemusí analyzovat každý jeden soubor.

AI se použije hlavně pro nejasný obsah nebo fotku bez čitelného textu. Na tomto počítači běží místní model na CPU, takže obrázková analýza může být pomalá a její popis může mít nízkou jistotu. Není to odborný posudek ani automatické rozhodnutí o plnění.

Při rozšíření na AI backloop by se model neměl volat pro každou fotku automaticky. Lepší je vyvolat ho jen při nízké jistotě OCR nebo chybějících důležitých polích. Tím se zpomalí jen obtížné dokumenty, běžné faktury zůstanou rychlé a zátěž místního modelu bude menší.

## Jak omezit falešná upozornění u konkrétní události

Jedna univerzální sada pravidel neví, co je důležité právě pro jednu konkrétní pojistnou událost. Když bude pravidlo příliš obecné, upozorní na spoustu neškodných rozdílů. Když bude příliš přísné, označí správný dokument jako chybný. Pomůže přidat ke každé události malý „profil případu“ a porovnávat dokumenty proti němu.

### 1. Nejdřív sestavit profil události

Z prvního spolehlivého hlášení nebo protokolu se založí sada známých údajů:

- číslo pojistné události,
- SPZ a VIN poškozeného vozidla,
- datum a místo nehody,
- jména účastníků a známý viník,
- druh škody, například střet vozidel nebo rozbité čelní sklo.

Každý údaj si drží zdroj. Například SPZ `7AK 2341` pochází z technického průkazu, datum z policejního protokolu. Když pozdější dokument uvádí `7AK2341`, jde nejspíš o stejnou SPZ bez mezery; před porovnáním se hodnoty normalizují.

### 2. Hledat jen body důležité pro daný dokument

Místo otázky „Je tenhle dokument špatně?“ se nejdřív zeptáme „Co potřebujeme ověřit právě u tohoto typu?“

| Dokument | Body, které dávají smysl kontrolovat |
|---|---|
| Faktura | dodavatel, číslo dokladu, datum, celková částka, měna, za co se platilo, případně SPZ/VIN |
| Policejní protokol | datum, místo, účastníci, vozidla, zavinění, zranění |
| Technický průkaz | SPZ, VIN, vlastník/provozovatel a značka vozidla |
| Lékařská zpráva | datum vyšetření, pacient, popsané zranění a souvislost s nehodou |
| Fotografie | co je na ní vidět a zda poškození odpovídá hlášené události |
| SMS/e-mail | kdo píše, číslo události u druhé pojišťovny, přiznání nebo doplnění průběhu |

Chybějící pole samo o sobě ještě neznamená špatný dokument. Fotka běžně nemá číslo faktury a protokol nemusí obsahovat cenu opravy. Upozornění vznikne až tehdy, když dokument tvrdí něco, co se důležitě rozchází s profilem případu.

### 3. Oddělit tři druhy výsledku

- **Souhlasí:** údaj se shoduje po normalizaci, například stejné VIN s jinými mezerami.
- **Prověřit:** údaje se liší, ale existuje rozumné vysvětlení, například překlep v OCR nebo datum platby místo data nehody.
- **Silný rozpor:** dva důvěryhodné zdroje tvrdí neslučitelné věci, například jiné VIN v technickém průkazu a na faktuře.

U každého upozornění je užitečné zobrazit také důvod a citovaný úsek zdrojového dokumentu. Likvidátor pak nemusí hledat, proč pravidlo spustilo výstrahu. Automatika by neměla dokument potichu zahodit ani sama rozhodnout o zamítnutí nároku.

### 4. Jak to rozvíjet bez zbytečného flagování

Nejdřív vytvoř sadu správně označených příkladů: „správná faktura“, „faktura s jinou SPZ“, „doklad, který k události nepatří“. Na těchto příkladech měř dvě chyby zvlášť:

- **falešný poplach:** správný dokument dostal varování,
- **přehlédnutí:** skutečný rozpor zůstal bez varování.

Pak upravuj konkrétní pravidlo, které chybu způsobilo. Například před porovnáním SPZ odstraň mezery a pomlčky, u částek porovnávej měnu zvlášť a nedělej z chybějícího protokolu automaticky podezření, pokud daný typ nehody protokol nevyžaduje. Každá oprava se přidá jako testovací případ, aby se stejná chyba nevrátila.

Ve větším systému by profil události a extrahovaná pole šla ukládat do databáze; OCR/AI úlohy by běžely ve frontě na samostatných workerech a kontroly by měly verzovaná pravidla. To je způsob, jak obsloužit více případů současně. Nejdřív se ale vyplatí zpřesnit datové body a testy: samotné přidání serverů špatná pravidla neopraví.

## Proč se stejný dokument nezapočítá dvakrát

Aplikace počítá kontrolní otisk obsahu souboru, zjednodušeně jeho digitální „otisk prstu“. Když dorazí stejný obsah znovu a původní archivní kopie existuje, novou kopii přeskočí a v souhrnu přidá upozornění.

Pokud databáze o dokumentu ví, ale archivní soubor chybí, nahraný soubor se zpracuje znovu místo smazání. To chrání před situací, kdy někdo smaže výslednou složku, ale aplikace si ještě pamatuje starý stav.

## Co dělat při zkoušení

1. Spusť `./spustit.sh` nebo jednorázově `./spustit.sh --jednou`.
2. Zkopíruj soubory z jedné scénářové složky do `klient_upload/`.
3. Sleduj terminál: vypíše typ a cestu, kam každý soubor přesunul.
4. Otevři `roztridene/SOUHRN_pojistne_udalosti.html`.
5. Když se něco nepovede, otevři nejnovější soubor `logs/run_*.log`.
6. Před novým čistým pokusem ukonči běžící watcher pomocí `Ctrl+C` a spusť `./vycistit.sh`.

Testovací scénáře jsou smyšlené a generátor je v `vytvor_testovaci_dokumenty.py`. Jeho spuštění znovu vytvoří základní dokumenty, náročné případy i scénářové složky.

## Slovníček bez žargonu

- **Složka/inbox:** místo, kam se odkládají nové soubory.
- **OCR:** čtení písmen z obrázku nebo skenu.
- **Klasifikace:** rozhodnutí, zda jde například o fakturu nebo protokol.
- **Extrakce:** vytažení částky, SPZ, data a podobných polí z textu.
- **Normalizace:** převod různých zápisů do stejného formátu, aby šly porovnat.
- **Fallback:** záložní cesta, která se použije, když AI selže.
- **Hash/otisk:** krátká hodnota vypočítaná z obsahu souboru, která pomůže poznat stejný obsah pod jiným názvem.
- **Pipeline:** několik kroků za sebou, kde výstup jednoho kroku používá krok další.
