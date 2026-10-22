"""Načtení a základní validace vstupních dat pro vizualizaci."""

from pathlib import Path
from typing import BinaryIO

import pandas as pd


def nacti_csv(soubor: str | Path | BinaryIO) -> tuple[pd.DataFrame, dict]:
    """Načte CSV s výstupem simulace a vrátí data spolu s validačním reportem.

    Sloupce oddělené čárkou, desetinná tečka (výchozí chování pandas).

    Args:
        soubor: cesta k souboru nebo file-like objekt (např. z st.file_uploader).

    Returns:
        Dvojice (data, report). `report` obsahuje:
            - "pocet_radku": int
            - "sloupce": list názvů sloupců
            - "ciselne_sloupce": list číselných sloupců (kandidáti na veličiny)
            - "chybejici_hodnoty": dict {sloupec: počet chybějících hodnot},
              obsahuje jen sloupce s alespoň jednou chybějící hodnotou
            - "duplicitni_radky": int
    """
    data = pd.read_csv(soubor)

    ciselne_sloupce = data.select_dtypes(include="number").columns.tolist()
    chybejici = data.isna().sum()
    chybejici_hodnoty = {sl: int(pocet) for sl, pocet in chybejici.items() if pocet > 0}

    report = {
        "pocet_radku": len(data),
        "sloupce": data.columns.tolist(),
        "ciselne_sloupce": ciselne_sloupce,
        "chybejici_hodnoty": chybejici_hodnoty,
        "duplicitni_radky": int(data.duplicated().sum()),
    }

    return data, report


def load_vensim(source: str | Path | BinaryIO, sep: str = "\t") -> pd.DataFrame:
    """Načte export z Vensimu v libovolné orientaci.

    Vensim exportuje data ve dvou orientacích:
        - čas v řádcích (první sloupec = čas, veličiny ve sloupcích),
        - transponovaná (první řádek = čas, veličiny v řádcích).
    Orientaci poznáme podle buňky pod levým horním rohem: v první variantě je tam
    číslo (první časový krok), ve druhé název další veličiny (text).

    Args:
        source: cesta k souboru nebo file-like objekt (např. z st.file_uploader).
        sep: oddělovač sloupců, Vensim exportuje s tabulátorem.

    Returns:
        DataFrame, kde index = čas (název indexu = původní název, např. "Time (Day)")
        a sloupce = veličiny bez přípony " : current".

    Raises:
        ValueError: soubor nemá očekávaný tvar nebo obsahuje nečíselné hodnoty.
    """
    raw = pd.read_csv(source, sep=sep, header=None)  # hlavičku určíme sami podle orientace
    raw = raw.dropna(axis=1, how="all")  # tabulátor na konci řádku vytvoří sloupec samých NaN

    if raw.shape[0] < 2 or raw.shape[1] < 2:
        raise ValueError(
            "Soubor má málo řádků nebo sloupců. Nevypadá jako export z Vensimu "
            "(nebo má jiný oddělovač než tabulátor)."
        )

    time_in_rows = pd.notna(pd.to_numeric(raw.iloc[1, 0], errors="coerce"))
    if not time_in_rows:
        raw = raw.T  # otočíme, aby byl čas v řádcích

    raw.columns = raw.iloc[0]  # první řádek obsahuje názvy sloupců
    try:
        df = raw.iloc[1:].astype(float)  # zbytek jsou čísla, zatím uložená jako text
    except ValueError as err:
        raise ValueError(
            "Data obsahují nečíselné hodnoty. Zkontroluj formát souboru a oddělovač."
        ) from err

    df.columns = df.columns.str.replace(" : current", "", regex=False)
    df.columns.name = None  # po přiřazení řádku jako hlavičky zůstane zbytečný název "0"

    return df.set_index(df.columns[0])  # čas = první sloupec, bez ohledu na jednotku


def time_window(df: pd.DataFrame, start: float, end: float) -> pd.DataFrame:
    """Vrátí výřez dat v časovém rozsahu <start, end> (oba kraje včetně).

    Malá tolerance ošetří nepřesnost desetinných čísel (např. 0.1 + 0.2 != 0.3).
    """
    if start > end:
        raise ValueError("Začátek časového rozsahu musí být před koncem.")
    tolerance = 1e-9 * max(1.0, abs(end - start))
    mask = (df.index >= start - tolerance) & (df.index <= end + tolerance)
    return df[mask]


def data_report(df: pd.DataFrame) -> dict:
    """Vrátí přehled o načtených datech pro kontrolu před vykreslením.

    Args:
        df: DataFrame z load_vensim (index = čas, sloupce = veličiny).

    Returns:
        Slovník s klíči:
            - "rows": int, počet časových kroků
            - "series": list názvů veličin
            - "time_start", "time_end": float, první a poslední čas
            - "time_step": float | None, typický krok času (medián rozdílů),
              None při jediném řádku
            - "time_increasing": bool, zda čas roste (jinak by animace neměla smysl)
            - "missing": dict {veličina: počet chybějících hodnot}, jen veličiny s alespoň jednou
    """
    step = df.index.to_series().diff().median()
    missing = df.isna().sum()

    return {
        "rows": len(df),
        "series": df.columns.tolist(),
        "time_start": float(df.index.min()),
        "time_end": float(df.index.max()),
        "time_step": None if pd.isna(step) else float(step),
        "time_increasing": bool(df.index.is_monotonic_increasing),
        "missing": {col: int(n) for col, n in missing.items() if n > 0},
    }
