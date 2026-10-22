"""Sestavení statického a animovaného grafu.

Vstupem je DataFrame z model.loaders.load_vensim (index = čas, sloupce = veličiny).

Grafy vytváříme přes matplotlib.figure.Figure, ne přes pyplot: pyplot si pamatuje
všechny otevřené figury (ve Streamlitu by paměť rostla s každým přepočtem) a
nepotřebuje se nastavovat backend "Agg".
"""

import pandas as pd
from matplotlib.animation import FuncAnimation
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from viz.style import (
    DEFAULT_Y_LABEL,
    FIGSIZE,
    FONT_SIZE,
    LINE_WIDTH,
    apply_theme,
    check_secondary,
    series_styles,
    setup_axes,
    setup_secondary_axis,
    y_limits,
)

DEFAULT_FPS = 12


def sample_frames(df: pd.DataFrame, step: int = 1) -> pd.DataFrame:
    """Vybere každý step-tý řádek; poslední krok přidá vždy, aby animace skončila na konci dat."""
    if step < 1:
        raise ValueError("Krok (step) musí být alespoň 1.")
    sampled = df.iloc[::step]
    if sampled.index[-1] != df.index[-1]:  # poslední krok mohl při vynechávání vypadnout
        sampled = pd.concat([sampled, df.iloc[[-1]]])
    return sampled


def _build_chart(
    df: pd.DataFrame,
    columns: list[str] | None,
    y_label: str,
    colors: list[str] | None,
    line_styles: list | None,
    secondary: list[str] | None,
    y2_label: str,
    figsize: tuple[float, float],
    line_width: float,
    dark: bool,
    transparent: bool,
) -> tuple[Figure, dict[str, Line2D]]:
    """Sestaví graf se všemi daty; společný základ statického grafu i animace.

    Meze os jsou pevné podle dat, aby se při animaci neposouvaly.
    Legenda je nad grafem: vpravo by kolidovala s pravou osou y a uvnitř grafu
    by v animaci nevěděla, kam se umístit (v prvním snímku jsou čáry prázdné).

    Returns:
        Figura a slovník {veličina: čára}.
    """
    columns = columns or df.columns.tolist()
    secondary = list(secondary or [])
    styles = series_styles(columns, colors, line_styles)
    check_secondary(columns, secondary)

    fig = Figure(figsize=figsize)
    ax = fig.add_subplot()
    ax2 = ax.twinx() if secondary else None  # druhá osa y se sdílenou osou x

    lines = {}  # název veličiny -> objekt čáry
    for column, color, style in styles:
        target = ax2 if column in secondary else ax
        (lines[column],) = target.plot(
            df.index, df[column], label=column, color=color, ls=style, lw=line_width
        )

    primary = [c for c in columns if c not in secondary]
    ax.set_xlim(df.index.min(), df.index.max())
    ax.set_ylim(*y_limits(df, primary))
    setup_axes(ax, df, y_label)
    axes = [ax]
    if ax2 is not None:
        ax2.set_ylim(*y_limits(df, secondary))
        setup_secondary_axis(ax2, y2_label)
        axes.append(ax2)

    # legendu kreslíme na horní vrstvu (pravou osu, pokud existuje), aby ji nic nepřekrylo;
    # u veličin na pravé ose to v legendě uvedeme, jinak by nebylo poznat, ke které ose patří
    labels = [f"{c} (pravá osa)" if c in secondary else c for c in lines]
    legend = axes[-1].legend(
        list(lines.values()),
        labels,
        loc="lower left",
        bbox_to_anchor=(0, 1.02),
        ncol=min(len(columns), 3),
        frameon=False,
        fontsize=FONT_SIZE,
    )
    apply_theme(fig, axes, legend, dark, transparent)
    fig.tight_layout()
    return fig, lines


def static_chart(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    y_label: str = DEFAULT_Y_LABEL,
    colors: list[str] | None = None,
    line_styles: list | None = None,
    *,
    secondary: list[str] | None = None,
    y2_label: str = "",
    figsize: tuple[float, float] = FIGSIZE,
    line_width: float = LINE_WIDTH,
    dark: bool = False,
    transparent: bool = False,
) -> Figure:
    """Vykreslí statický graf vybraných veličin (výchozí: všechny sloupce).

    Args:
        df: data (index = čas, sloupce = veličiny).
        columns: vybrané veličiny.
        y_label: popisek levé osy y.
        colors, line_styles: barvy a typy čar v pořadí veličin (výchozí: paleta a styly).
        secondary: veličiny, které se kreslí na pravou osu y.
        y2_label: popisek pravé osy y.
        figsize: velikost grafu v palcích.
        line_width: tloušťka čar.
        dark: tmavý motiv (světlý text a osy na tmavém pozadí).
        transparent: průhledné pozadí.
    """
    fig, _ = _build_chart(
        df,
        columns,
        y_label=y_label,
        colors=colors,
        line_styles=line_styles,
        secondary=secondary,
        y2_label=y2_label,
        figsize=figsize,
        line_width=line_width,
        dark=dark,
        transparent=transparent,
    )
    return fig


def animated_chart(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    y_label: str = DEFAULT_Y_LABEL,
    step: int = 1,
    fps: int = DEFAULT_FPS,
    colors: list[str] | None = None,
    line_styles: list | None = None,
    *,
    secondary: list[str] | None = None,
    y2_label: str = "",
    figsize: tuple[float, float] = FIGSIZE,
    line_width: float = LINE_WIDTH,
    dark: bool = False,
    transparent: bool = False,
) -> tuple[Figure, FuncAnimation]:
    """Sestaví animaci postupného vykreslování vybraných veličin v čase (neukládá ji).

    Parametry vzhledu jsou stejné jako u static_chart; step = každý n-tý krok simulace.
    """
    columns = columns or df.columns.tolist()
    data = sample_frames(df[columns], step)
    fig, lines = _build_chart(
        df,
        columns,
        y_label=y_label,
        colors=colors,
        line_styles=line_styles,
        secondary=secondary,
        y2_label=y2_label,
        figsize=figsize,
        line_width=line_width,
        dark=dark,
        transparent=transparent,
    )
    for line in lines.values():  # graf je hotový i s mezemi os, čáry vyprázdníme
        line.set_data([], [])

    def update(i):
        """Pro snímek i dosadí do čar data od začátku po i-tý řádek (podle pozice)."""
        visible = data.iloc[: i + 1]
        for column, line in lines.items():
            line.set_data(visible.index, visible[column])
        return list(lines.values())  # blit=True potřebuje seznam změněných objektů

    ani = FuncAnimation(fig, update, frames=len(data), interval=1000 / fps, blit=True)
    return fig, ani
