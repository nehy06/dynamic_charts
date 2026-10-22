# 📈 Dynamické grafy ze systémové dynamiky

Streamlit aplikace, která z exportu modelu systémové dynamiky (Vensim) vytvoří
**animovaný graf (GIF)** pro vložení do prezentace v PowerPointu.

PowerPoint neumí vložit živý interaktivní graf. Animovaný GIF je spolehlivá cesta, jak na
slidu ukázat vývoj veličin v čase. GIF se ve výchozím nastavení přehraje jednou a zůstane
stát na hotovém grafu.

## Co aplikace umí

1. **Nahrání exportu z Vensimu** – obě orientace (čas v řádcích i ve sloupcích), kontrola dat.
2. **Náhled dat** – počet kroků, rozsah a krok času, chybějící hodnoty, tabulka.
3. **Nastavení grafu**
   - výběr veličin (nejvýš 5) a časového rozsahu,
   - popisek osy y, **druhá osa y** pro veličiny v jiném řádu,
   - palety barev (vč. palet pro barvoslepé a barev PowerPointu), barva a typ čáry pro každou
     veličinu, tloušťka čar,
   - velikost podle slidu 16:9, ostrost (DPI), **průhledné pozadí**, **tmavý motiv**.
4. **Statický graf** se stažením PNG.
5. **Animace** – každý n-tý krok, fps, smyčka; náhled a stažení GIFu.

## Vstupní data

Textový soubor z Vensimu, hodnoty oddělené **tabulátorem**. Podporované orientace:

| Čas v řádcích | Čas ve sloupcích (transponovaný) |
|---|---|
| `Time (Day)  progress : current  Work done : current`<br>`0  2  0`<br>`0.125  2.00027  0.25` | `Time (Day)  0  0.125  0.25 …`<br>`progress : current  2  2.00027 …`<br>`Work done : current  0  0.25 …` |

- Orientaci aplikace pozná sama.
- Přípona ` : current` se z názvů odstraní.
- Jednotka času se vezme ze závorky (`Time (Day)` → osa „Čas (dny)“).
- Vensim neexportuje jednotky veličin – popisek osy y se zadává ručně.

Vstupní data nejsou součástí repozitáře. Lokálně je můžeš mít ve složce `data/`
(je v `.gitignore`).

## Spuštění lokálně (Linux / WSL)

```bash
git clone git@github.com:nehy06/dynamic_charts.git
cd dynamic_charts

python3 -m venv .venv            # virtuální prostředí (jednorázově)
source .venv/bin/activate        # aktivace (v každém novém terminálu)
pip install -r requirements.txt

streamlit run app.py
```

Aplikace se otevře na <http://localhost:8501> (z WSL funguje i v prohlížeči ve Windows).

> Ve WSL může `python3 -m venv` hlásit chybějící `ensurepip` – pak je potřeba jednorázově
> `sudo apt install python3-venv`.

## Testy a kontrola kódu

```bash
pytest -v           # automatické testy (složka tests/, soubory test_*.py)
ruff check .        # kontrola stylu a chyb
ruff format .       # formátování (délka řádku 100)
```

## Struktura projektu

```
app.py              # Streamlit UI – jen widgety a volání funkcí
model/
    loaders.py      # načtení exportu z Vensimu, výřez času, přehled dat
viz/
    style.py        # palety, typy čar, motivy, formát os, druhá osa y
    animation.py    # statický graf a animace (matplotlib Figure + FuncAnimation)
    export.py       # export GIF (bez smyčky) a PNG, odhad paměti
tests/              # pytest testy
pyproject.toml      # nastavení pytest a ruff
requirements.txt    # závislosti
```

## Nasazení na Streamlit Community Cloud

1. Repozitář musí být na GitHubu. Aplikace se nasazuje z větve `main`.
2. Na <https://share.streamlit.io> se přihlas přes GitHub → **Create app** → **Deploy a public app from GitHub**.
3. Vyplň:
   - **Repository:** `nehy06/dynamic_charts`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. V **Advanced settings** zvol verzi Pythonu. Projekt je vyvíjený a testovaný na 3.14.
   Pokud ji Cloud nenabízí, zvol nejvyšší dostupnou a po nasazení aplikaci vyzkoušej.
5. **Deploy.** Závislosti se nainstalují z `requirements.txt` automaticky.

Po každém `git push` do `main` se aplikace na Cloudu sama aktualizuje.

**Dobré vědět:**

- Aplikace nepotřebuje žádné tajné údaje (`secrets`) ani databázi.
- Nahraná data se nikam neukládají, drží se jen v paměti po dobu práce s aplikací.
  Přesto do veřejně nasazené aplikace nenahrávej citlivá data.
- Cloud má **omezenou paměť**. Snímky animace se drží v paměti, proto aplikace odhadne
  potřebnou paměť a nad 800 MB generování nepustí (limit `MAX_MEMORY_MB` ve
  `viz/export.py`). Pomůže vyšší „každý n-tý krok“, nižší DPI nebo menší velikost grafu.
- Nepoužívaná aplikace na Cloudu po čase „usne“. Probudí se tlačítkem při další návštěvě.

## Známá omezení

- Nejvýš 5 veličin v jednom grafu (přehlednost na projektoru).
- Průhledné pozadí v GIFu: GIF umí jen plnou průhlednost, okraje písma a čar proto mohou
  být na barevném slidu mírně zubaté. V PNG je průhlednost plynulá.
- Velikost GIFu nad 5 MB aplikace hlásí – prezentace pak bývá zbytečně velká.

## Licence

Viz [LICENSE](LICENSE).
