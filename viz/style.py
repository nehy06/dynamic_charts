"""Jednotný vzhled grafů: barvy, styly čar, písmo a formát os."""

import re

import matplotlib.ticker as mticker
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.legend import Legend

# víc veličin v jednom grafu už je na projektoru nepřehledné
MAX_SERIES = 5

# palety k výběru, každá má alespoň MAX_SERIES barev
PALETTES = {
    "Výchozí (přátelská k barvosleposti)": ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3"],
    "Okabe-Ito (pro barvoslepé)": ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"],
    "Office (barvy PowerPointu)": ["#4472C4", "#ED7D31", "#70AD47", "#FFC000", "#5B9BD5"],
    "Tableau (výchozí matplotlib)": ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD"],
    "Odstíny šedi (pro tisk)": ["#000000", "#404040", "#707070", "#909090", "#B0B0B0"],
}
DEFAULT_PALETTE = "Výchozí (přátelská k barvosleposti)"
PALETTE = PALETTES[DEFAULT_PALETTE]

# typy čar k výběru: český název -> zápis pro matplotlib
LINE_STYLE_OPTIONS = {
    "plná": "-",
    "čárkovaná": "--",
    "čerchovaná": "-.",
    "tečkovaná": ":",
    "dlouhá čárka": (0, (8, 3)),
}
# výchozí styly v pořadí veličin - série jdou rozlišit i bez barev
LINE_STYLES = list(LINE_STYLE_OPTIONS.values())

# graf poputuje na projektor -> písmo min. 11 pt
FONT_SIZE = 12
LINE_WIDTH = 2

# velikost grafu v palcích podle slidu PowerPointu (16:9 = 13,33 × 7,5 palce);
# při vložení do slidu v reálné velikosti má pak písmo opravdu FONT_SIZE bodů
FIGSIZES = {
    "Obsah slidu pod nadpisem (16:9)": (12.3, 5.5),
    "Celý slide (16:9)": (13.33, 7.5),
    "Polovina slidu": (6.2, 5.5),
    "Široký nízký (2:1)": (10, 5),
}
DEFAULT_FIGSIZE = "Obsah slidu pod nadpisem (16:9)"
FIGSIZE = FIGSIZES[DEFAULT_FIGSIZE]

# barvy textu, os a pozadí pro světlý a tmavý motiv
THEMES = {
    "light": {"foreground": "#000000", "background": "#FFFFFF"},
    "dark": {"foreground": "#E6E6E6", "background": "#1E1E1E"},
}

# překlad jednotek času z Vensimu do popisku osy x, např. "Time (Day)" -> "Čas (dny)"
TIME_UNITS = {"Day": "dny", "Week": "týdny", "Month": "měsíce", "Year": "roky", "Hour": "hodiny"}

DEFAULT_Y_LABEL = "Hodnota"


def time_unit(df: pd.DataFrame) -> str:
    """Vrátí českou jednotku času z názvu indexu, např. "Time (Day)" -> "dny".

    Neznámou jednotku vrátí beze změny, index bez závorky vrátí celý název.
    """
    match = re.search(r"\((.+)\)", str(df.index.name))
    if not match:
        return str(df.index.name)
    return TIME_UNITS.get(match.group(1), match.group(1))


def format_number(x: float, _pos=None) -> str:
    """Formátovač osy: velká čísla zkrátí na tisíce / miliony."""
    if abs(x) >= 1e6:
        return f"{x / 1e6:g} mil."
    if abs(x) >= 1e3:
        return f"{x / 1e3:g} tis."
    return f"{x:g}"


def check_series_count(columns: list[str]) -> None:
    """Vyhodí chybu, pokud je vybraných veličin víc, než graf přehledně zobrazí."""
    if len(columns) > MAX_SERIES:
        raise ValueError(
            f"Vybráno {len(columns)} veličin, graf zobrazí přehledně nejvýš {MAX_SERIES}. "
            "Vyber méně veličin."
        )


def series_styles(
    columns: list[str],
    colors: list[str] | None = None,
    line_styles: list | None = None,
) -> list[tuple[str, str, str | tuple]]:
    """Přiřadí každé veličině barvu a typ čáry.

    Args:
        columns: vybrané veličiny.
        colors: barvy v pořadí veličin (výchozí: PALETTE).
        line_styles: typy čar v pořadí veličin ve formátu matplotlibu (výchozí: LINE_STYLES).

    Returns:
        Seznam trojic (veličina, barva, typ čáry).

    Raises:
        ValueError: příliš mnoho veličin nebo méně barev / stylů než veličin.
    """
    check_series_count(columns)
    colors = colors or PALETTE
    line_styles = line_styles or LINE_STYLES
    if len(colors) < len(columns) or len(line_styles) < len(columns):
        raise ValueError("Každá veličina musí mít přiřazenou barvu i typ čáry.")
    return list(zip(columns, colors, line_styles))


def check_secondary(columns: list[str], secondary: list[str]) -> None:
    """Ověří výběr veličin pro pravou osu y.

    Raises:
        ValueError: veličina na pravé ose není mezi vybranými, nebo na levé ose nic nezbylo.
    """
    unknown = [c for c in secondary if c not in columns]
    if unknown:
        raise ValueError(f"Veličiny {unknown} pro pravou osu nejsou mezi vybranými veličinami.")
    if secondary and len(secondary) == len(columns):
        raise ValueError("Na levé ose musí zůstat alespoň jedna veličina.")


def y_limits(df: pd.DataFrame, columns: list[str], margin: float = 0.05) -> tuple[float, float]:
    """Spočítá meze osy y s rezervou odvozenou z rozpětí dat.

    Rezerva z rozpětí funguje i pro záporné hodnoty a nulu (na rozdíl od min * 0.95).
    """
    lower = df[columns].min().min()
    upper = df[columns].max().max()
    pad = (upper - lower) * margin
    if pad == 0:  # konstantní data - rozpětí je nulové, rezervu odvodíme z hodnoty
        pad = abs(upper) * margin or 1
    return lower - pad, upper + pad


def setup_axes(ax: Axes, df: pd.DataFrame, y_label: str) -> None:
    """Nastaví popisky os, velikost písma, formát čísel a skryje horní a pravý rámeček."""
    ax.set_xlabel(f"Čas ({time_unit(df)})", fontsize=FONT_SIZE)
    ax.set_ylabel(y_label, fontsize=FONT_SIZE)
    ax.tick_params(labelsize=FONT_SIZE)
    ax.spines[["top", "right"]].set_visible(False)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(format_number))


def setup_secondary_axis(ax: Axes, y_label: str) -> None:
    """Nastaví pravou osu y (vytvořenou přes ax.twinx()): popisek, písmo, formát čísel."""
    ax.set_ylabel(y_label, fontsize=FONT_SIZE)
    ax.tick_params(labelsize=FONT_SIZE)
    ax.spines[["top", "left"]].set_visible(False)  # levou osu kreslí hlavní osa
    ax.spines["right"].set_visible(True)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(format_number))


def apply_theme(
    fig: Figure, axes: list[Axes], legend: Legend, dark: bool = False, transparent: bool = False
) -> None:
    """Obarví text, osy a pozadí podle motivu; volitelně udělá pozadí průhledné.

    Průhlednost se nastaví přímo na figuře, takže platí pro náhled, PNG i GIF.
    """
    theme = THEMES["dark" if dark else "light"]
    fg, bg = theme["foreground"], theme["background"]

    fig.patch.set_facecolor(bg)
    fig.patch.set_alpha(0 if transparent else 1)
    axes[0].set_facecolor(bg)  # pozadí kreslí jen hlavní osa, pravá osa je průhledná vrstva
    axes[0].patch.set_alpha(0 if transparent else 1)

    for ax in axes:
        ax.tick_params(colors=fg)  # značky i čísla na osách
        ax.xaxis.label.set_color(fg)
        ax.yaxis.label.set_color(fg)
        for spine in ax.spines.values():
            spine.set_color(fg)
    for text in legend.get_texts():
        text.set_color(fg)
