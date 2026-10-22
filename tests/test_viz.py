"""Testy vzhledu, animace a exportu (balíček viz)."""

from io import BytesIO

import pandas as pd
import pytest
from PIL import Image

from viz.animation import animated_chart, sample_frames, static_chart
from viz.export import estimate_memory_mb, export_gif, export_png
from viz.style import (
    LINE_STYLE_OPTIONS,
    MAX_SERIES,
    PALETTES,
    THEMES,
    check_secondary,
    check_series_count,
    format_number,
    series_styles,
    time_unit,
    y_limits,
)


@pytest.fixture
def small_df():
    """Malá ukázková data: 9 časových kroků, 2 veličiny.

    Fixture = připravená data, která si test vyžádá parametrem se stejným jménem.
    """
    index = pd.Index([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0], name="Time (Day)")
    return pd.DataFrame({"a": range(9), "b": range(-4, 5)}, index=index, dtype=float)


# --- style ---


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Time (Day)", "dny"),
        ("Time (Month)", "měsíce"),
        ("Time (Decade)", "Decade"),
        ("rok", "rok"),
    ],
)
def test_time_unit(name, expected):
    """parametrize = jeden test spuštěný pro několik vstupů."""
    df = pd.DataFrame({"x": [1]}, index=pd.Index([0], name=name))
    assert time_unit(df) == expected


def test_format_number():
    assert format_number(2_500_000) == "2.5 mil."
    assert format_number(1500) == "1.5 tis."
    assert format_number(12) == "12"


def test_y_limits_with_negative_values(small_df):
    """Rezerva z rozpětí: dolní mez musí být pod minimem i u záporných čísel."""
    lower, upper = y_limits(small_df, ["a", "b"])
    assert lower < -4
    assert upper > 8


def test_y_limits_constant_data():
    df = pd.DataFrame({"a": [5.0, 5.0, 5.0]})
    lower, upper = y_limits(df, ["a"])
    assert lower < 5 < upper


def test_too_many_series():
    with pytest.raises(ValueError):
        check_series_count(["a", "b", "c", "d", "e", "f"])


@pytest.mark.parametrize("name", list(PALETTES))
def test_palettes_have_enough_valid_colors(name):
    """Každá paleta musí pokrýt maximální počet veličin platnými barvami #RRGGBB."""
    colors = PALETTES[name]
    assert len(colors) >= MAX_SERIES
    assert all(c.startswith("#") and len(c) == 7 for c in colors)


def test_series_styles_defaults():
    styles = series_styles(["a", "b"])
    assert [column for column, _, _ in styles] == ["a", "b"]
    assert styles[0][2] != styles[1][2]  # výchozí typy čar se liší


def test_series_styles_not_enough_colors():
    with pytest.raises(ValueError, match="barvu i typ čáry"):
        series_styles(["a", "b"], colors=["#000000"])


# --- animation ---


def test_sample_frames_keeps_last_step(small_df):
    sampled = sample_frames(small_df, step=3)  # řádky 0, 3, 6 + poslední 8
    assert sampled.index.tolist() == [0.0, 1.5, 3.0, 4.0]


def test_sample_frames_no_duplicate_last(small_df):
    sampled = sample_frames(small_df, step=4)  # řádky 0, 4, 8 - poslední už je
    assert sampled.index.tolist() == [0.0, 2.0, 4.0]


def test_static_chart_labels(small_df):
    fig = static_chart(small_df, y_label="FTE")
    ax = fig.axes[0]
    assert ax.get_xlabel() == "Čas (dny)"
    assert ax.get_ylabel() == "FTE"
    assert len(ax.lines) == 2


def test_static_chart_custom_colors_and_styles(small_df):
    """Zvolené barvy a typy čar se musí v grafu opravdu použít."""
    fig = static_chart(
        small_df,
        colors=["#FF0000", "#00FF00"],
        line_styles=[LINE_STYLE_OPTIONS["tečkovaná"], LINE_STYLE_OPTIONS["plná"]],
    )
    line_a, line_b = fig.axes[0].lines
    assert line_a.get_color() == "#FF0000"
    assert line_a.get_linestyle() == ":"
    assert line_b.get_linestyle() == "-"


def test_animated_chart_custom_colors(small_df):
    fig, _ = animated_chart(small_df, colors=["#123456", "#654321"])
    assert [line.get_color() for line in fig.axes[0].lines] == ["#123456", "#654321"]


def test_secondary_axis(small_df):
    """Veličina "b" jde na pravou osu: graf má 2 osy, na každé jednu čáru."""
    fig = static_chart(small_df, y_label="levá", secondary=["b"], y2_label="pravá")
    ax, ax2 = fig.axes
    assert [line.get_label() for line in ax.lines] == ["a"]
    assert [line.get_label() for line in ax2.lines] == ["b"]
    assert ax2.get_ylabel() == "pravá"
    lower, upper = ax2.get_ylim()  # meze pravé osy podle "b" (-4 až 4), ne podle "a"
    assert lower < -4 and 4 < upper < 8
    legend_texts = [t.get_text() for t in ax2.get_legend().get_texts()]
    assert legend_texts == ["a", "b (pravá osa)"]


def test_without_secondary_axis_single_axes(small_df):
    assert len(static_chart(small_df).axes) == 1


@pytest.mark.parametrize(
    "secondary, message",
    [(["x"], "nejsou mezi vybranými"), (["a", "b"], "alespoň jedna veličina")],
)
def test_check_secondary_errors(secondary, message):
    with pytest.raises(ValueError, match=message):
        check_secondary(["a", "b"], secondary)


def test_figsize(small_df):
    fig = static_chart(small_df, figsize=(6.2, 5.5))
    assert tuple(fig.get_size_inches()) == pytest.approx((6.2, 5.5))


def test_line_width(small_df):
    fig = static_chart(small_df, line_width=4)
    assert all(line.get_linewidth() == 4 for line in fig.axes[0].lines)


def test_dark_theme(small_df):
    """Tmavý motiv: světlý popisek osy na tmavém pozadí."""
    fig = static_chart(small_df, dark=True)
    ax = fig.axes[0]
    assert ax.xaxis.label.get_color() == THEMES["dark"]["foreground"]
    assert fig.patch.get_facecolor()[:3] == pytest.approx((30 / 255, 30 / 255, 30 / 255))


def test_animation_keeps_axis_limits(small_df):
    """Animace začíná s prázdnými čarami, ale meze os jsou už nastavené podle celých dat."""
    fig, _ = animated_chart(small_df, secondary=["b"])
    ax, ax2 = fig.axes
    assert len(ax.lines[0].get_xdata()) == 0
    assert ax.get_xlim() == (0.0, 4.0)
    assert ax2.get_ylim()[0] < -4


# --- export ---


def test_png_export(small_df):
    data = export_png(static_chart(small_df))
    assert data.startswith(b"\x89PNG")  # každý PNG soubor začíná tímto "podpisem"


def test_png_transparent(small_df):
    """Průhledné pozadí: roh obrázku má alfa kanál 0 (úplně průhledný)."""
    image = Image.open(BytesIO(export_png(static_chart(small_df, transparent=True))))
    assert image.mode == "RGBA"
    assert image.getpixel((0, 0))[3] == 0


def test_gif_transparent(small_df):
    """GIF s průhledným pozadím má v hlavičce nastavenou průhlednou barvu."""
    _, ani = animated_chart(small_df, step=4, transparent=True)
    image = Image.open(BytesIO(export_gif(ani)))
    assert "transparency" in image.info


def test_estimate_memory():
    # 10 snímků × (10 × 100) × (5 × 100) pixelů × 3 bajty = 15 MB
    assert estimate_memory_mb(10, (10, 5), 100) == pytest.approx(15)
    assert estimate_memory_mb(10, (10, 5), 100, transparent=True) == pytest.approx(20)


def test_gif_plays_once(small_df):
    """GIF bez smyčky nesmí obsahovat blok NETSCAPE2.0, který říká "opakuj"."""
    _, ani = animated_chart(small_df, step=2)
    data = export_gif(ani)
    assert data.startswith(b"GIF8")
    assert b"NETSCAPE2.0" not in data


def test_gif_loop(small_df):
    _, ani = animated_chart(small_df, step=2)
    data = export_gif(ani, loop=True)
    assert b"NETSCAPE2.0" in data


def test_gif_progress_callback(small_df):
    """progress_callback se zavolá pro každý snímek (sem napojíme st.progress)."""
    calls = []
    _, ani = animated_chart(small_df, step=2)  # 5 snímků
    export_gif(ani, progress_callback=lambda i, n: calls.append((i, n)))
    assert len(calls) == 5
    assert calls[-1] == (4, 5)
