"""Streamlit aplikace: animované grafy z exportů Vensimu pro prezentace v PowerPointu.

Spuštění: streamlit run app.py

Streamlit při každé akci uživatele spustí tento skript celý znovu od začátku.
Proto je načítání dat cachované (@st.cache_data) a logika je v model/ a viz/,
tady je jen UI.
"""

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from model.loaders import data_report, load_vensim, time_window
from viz.animation import DEFAULT_FPS, animated_chart, sample_frames, static_chart
from viz.export import (
    DPI_OPTIONS,
    MAX_MEMORY_MB,
    MAX_SIZE_MB,
    estimate_memory_mb,
    export_gif,
    export_png,
    size_mb,
)
from viz.style import (
    DEFAULT_FIGSIZE,
    DEFAULT_PALETTE,
    DEFAULT_Y_LABEL,
    FIGSIZES,
    LINE_STYLE_OPTIONS,
    MAX_SERIES,
    PALETTES,
    time_unit,
)

st.set_page_config(page_title="Dynamické grafy", page_icon="📈", layout="wide")


@st.cache_data
def load_cached(file_bytes: bytes) -> pd.DataFrame:
    """Načte export z obsahu souboru.

    Cache se řídí obsahem souboru: při dalším spuštění skriptu se stejný soubor
    nečte znovu, Streamlit vrátí uložený výsledek.
    """
    return load_vensim(BytesIO(file_bytes))


def format_time(value: float) -> str:
    """Čas bez zbytečných desetinných míst (100.0 -> "100", 0.125 -> "0.125")."""
    return f"{value:g}"


st.title("📈 Dynamické grafy ze systémové dynamiky")
st.caption(
    "Z exportu z Vensimu vytvoří animovaný graf (GIF) pro vložení do PowerPointu. "
    "Podporuje obě orientace exportu – čas v řádcích i ve sloupcích."
)

# --- 1. Nahrání souboru ---

with st.sidebar:
    st.header("1. Data")
    uploaded = st.file_uploader(
        "Export z Vensimu",
        type=["txt", "tsv", "csv"],
        help="Textový soubor s hodnotami oddělenými tabulátorem (výchozí export z Vensimu).",
    )

if uploaded is None:
    st.info("👈 Začni nahráním exportu z Vensimu v bočním panelu.")
    st.stop()  # zbytek skriptu se bez dat nespustí

try:
    df = load_cached(uploaded.getvalue())
except ValueError as err:  # vlastní chyby z load_vensim i chyby čtení z pandas
    st.error(f"Soubor **{uploaded.name}** se nepodařilo načíst.\n\n{err}")
    st.stop()

# --- 2. Náhled a kontrola dat ---

report = data_report(df)
unit = time_unit(df)

st.header("2. Náhled dat")
st.write(f"Soubor **{uploaded.name}**")

col_rows, col_series, col_range, col_step = st.columns(4)
col_rows.metric("Časových kroků", report["rows"])
col_series.metric("Veličin", len(report["series"]))
col_range.metric(
    f"Rozsah času ({unit})",
    f"{format_time(report['time_start'])} – {format_time(report['time_end'])}",
)
col_step.metric(
    f"Krok času ({unit})",
    "–" if report["time_step"] is None else format_time(report["time_step"]),
)

if report["missing"]:
    missing = ", ".join(f"{name} ({count}×)" for name, count in report["missing"].items())
    st.warning(f"Chybějící hodnoty: {missing}. V grafu se v těchto místech čára přeruší.")
if not report["time_increasing"]:
    st.warning("Čas v datech neroste po krocích. Zkontroluj export, animace nemusí dávat smysl.")

with st.expander("Tabulka dat", expanded=False):
    st.dataframe(df, height=300)

with st.sidebar:
    if report["time_step"] is None:  # jediný časový krok - není co ořezávat
        time_range = (report["time_start"], report["time_end"])
    else:
        time_range = st.slider(
            f"Časový rozsah ({unit})",
            min_value=report["time_start"],
            max_value=report["time_end"],
            value=(report["time_start"], report["time_end"]),
            step=report["time_step"],
            help="Graf i animace ukážou jen vybraný úsek simulace.",
        )
df_view = time_window(df, *time_range)  # s tímto výřezem pracují všechny grafy

# --- 3. Nastavení a statický graf ---

with st.sidebar:
    st.header("2. Graf")
    columns = st.multiselect(
        "Veličiny",
        options=report["series"],
        default=report["series"][:MAX_SERIES],
        max_selections=MAX_SERIES,
        help=f"Nejvýš {MAX_SERIES} veličin – víc už je v grafu na projektoru nepřehledné.",
    )
    y_label = st.text_input(
        "Popisek osy y",
        value=DEFAULT_Y_LABEL,
        help="Vensim jednotky neexportuje, zadej je ručně, např. „FTE (přepočtený)“.",
    )

if not columns:
    st.info("👈 Vyber v bočním panelu alespoň jednu veličinu.")
    st.stop()

with st.sidebar:
    palette_names = list(PALETTES)
    palette_name = st.selectbox(
        "Paleta barev",
        options=palette_names,
        index=palette_names.index(DEFAULT_PALETTE),
        help="Výchozí barvy čar. Jednotlivé barvy můžeš změnit níže.",
    )
    palette = PALETTES[palette_name]
    style_names = list(LINE_STYLE_OPTIONS)

    colors, line_style_names = [], []
    with st.expander("Barvy a typy čar"):
        for i, column in enumerate(columns):
            st.markdown(f"**{column}**")
            col_color, col_style = st.columns([1, 3], vertical_alignment="center")
            # název palety je v klíči widgetu -> po změně palety se barvy přenastaví
            colors.append(
                col_color.color_picker(
                    f"Barva – {column}",
                    value=palette[i],
                    key=f"color_{palette_name}_{column}",
                    label_visibility="collapsed",
                )
            )
            line_style_names.append(
                col_style.selectbox(
                    f"Typ čáry – {column}",
                    options=style_names,
                    index=i % len(style_names),
                    key=f"line_style_{column}",
                    label_visibility="collapsed",
                )
            )
    line_width = st.slider("Tloušťka čáry", min_value=1.0, max_value=5.0, value=2.0, step=0.5)

    secondary = st.multiselect(
        "Na pravou osu y",
        options=columns,
        help="Pro veličiny v jiném řádu (např. 0–3 vedle 0–100). Mají vlastní měřítko vpravo.",
    )
    y2_label = ""
    if secondary:
        y2_label = st.text_input("Popisek pravé osy y", value=DEFAULT_Y_LABEL)

    st.subheader("Velikost a pozadí")
    figsize_name = st.selectbox(
        "Velikost grafu",
        options=list(FIGSIZES),
        index=list(FIGSIZES).index(DEFAULT_FIGSIZE),
        help="Podle slidu PowerPointu 16:9. Při vložení v plné velikosti má písmo 12 bodů.",
    )
    dpi_name = st.selectbox(
        "Ostrost (DPI)",
        options=list(DPI_OPTIONS),
        help="Vyšší DPI = ostřejší na projektoru, ale větší soubor a delší generování.",
    )
    transparent = st.checkbox(
        "Průhledné pozadí",
        help="Graf převezme pozadí slidu. U GIFu mohou být okraje písma a čar mírně zubaté "
        "(GIF umí jen plnou průhlednost, ne poloprůhlednost).",
    )
    dark = st.checkbox(
        "Tmavý motiv",
        help="Světlý text a osy pro tmavé slidy. Paleta „Odstíny šedi“ se na tmavé pozadí nehodí.",
    )

line_styles = [LINE_STYLE_OPTIONS[name] for name in line_style_names]
dpi = DPI_OPTIONS[dpi_name]

# všechny volby vzhledu pohromadě - stejné pro statický graf i animaci
chart_kwargs = {
    "colors": colors,
    "line_styles": line_styles,
    "secondary": secondary,
    "y2_label": y2_label,
    "figsize": FIGSIZES[figsize_name],
    "line_width": line_width,
    "dark": dark,
    "transparent": transparent,
}

file_stem = Path(uploaded.name).stem  # základ názvu pro stahované soubory

st.header("3. Statický graf")
try:
    fig = static_chart(df_view, columns, y_label, **chart_kwargs)
except ValueError as err:  # např. všechny veličiny na pravé ose
    st.error(str(err))
    st.stop()
st.pyplot(fig)
st.download_button(
    "⬇️ Stáhnout PNG",
    data=export_png(fig, dpi=dpi),
    file_name=f"{file_stem}.png",
    mime="image/png",
)

# --- 4. Animace ---

TARGET_FRAMES = 100  # výchozí krok volíme tak, aby animace měla zhruba tolik snímků

with st.sidebar:
    st.header("3. Animace")
    step = st.number_input(
        "Vykreslit každý n-tý krok",
        min_value=1,
        max_value=len(df_view),
        value=max(1, len(df_view) // TARGET_FRAMES),
        help="1 = každý krok simulace. Vyšší číslo = méně snímků, kratší animace, menší soubor.",
    )
    fps = st.slider("Snímků za sekundu (fps)", min_value=5, max_value=30, value=DEFAULT_FPS)
    loop = st.checkbox(
        "Opakovat ve smyčce",
        value=False,
        help="Vypnuto: animace se přehraje jednou a zůstane na hotovém grafu.",
    )

n_frames = len(sample_frames(df_view, step))
st.header("4. Animace")
st.write(f"**{n_frames}** snímků při {fps} fps → délka **{n_frames / fps:.1f} s**")

# snímky se drží v paměti až do uložení GIFu -> příliš velkou animaci nepustíme
memory_mb = estimate_memory_mb(n_frames, chart_kwargs["figsize"], dpi, transparent)
too_large = memory_mb > MAX_MEMORY_MB
if too_large:
    st.warning(
        f"Animace by při generování potřebovala asi {memory_mb:.0f} MB paměti "
        f"(limit {MAX_MEMORY_MB} MB). Zvyš „každý n-tý krok“, sniž ostrost (DPI) "
        "nebo zvol menší velikost grafu."
    )

# hotový GIF držíme v session_state, aby přežil další spuštění skriptu (např. klik na stažení);
# podle nastavení poznáme, jestli GIF odpovídá tomu, co je právě vybrané
settings = (
    uploaded.file_id,
    time_range,
    tuple(columns),
    y_label,
    repr(chart_kwargs),  # textová podoba slovníku - jde porovnat, i když obsahuje seznamy
    dpi,
    step,
    fps,
    loop,
)

if st.button("🎬 Vygenerovat animaci", type="primary", disabled=too_large):
    progress = st.progress(0.0, text="Generuji animaci…")

    def on_frame(i: int, n: int) -> None:
        """Posune progress bar po každém vykresleném snímku."""
        progress.progress((i + 1) / n, text=f"Generuji snímek {i + 1} z {n}…")

    _, ani = animated_chart(df_view, columns, y_label, step, fps, **chart_kwargs)
    gif = export_gif(ani, fps=fps, loop=loop, dpi=dpi, progress_callback=on_frame)
    progress.empty()
    st.session_state["animation"] = {"gif": gif, "settings": settings}

result = st.session_state.get("animation")
if result is None:
    st.info("Nastav parametry v bočním panelu a klikni na **Vygenerovat animaci**.")
elif result["settings"] != settings:
    st.info("Nastavení se od posledního generování změnilo. Vygeneruj animaci znovu.")
else:
    gif = result["gif"]
    if size_mb(gif) > MAX_SIZE_MB:
        st.warning(
            f"GIF má {size_mb(gif):.1f} MB (víc než {MAX_SIZE_MB} MB). Prezentace bude velká – "
            "zvaž vyšší „každý n-tý krok“."
        )
    st.image(gif)
    st.download_button(
        f"⬇️ Stáhnout GIF ({size_mb(gif):.1f} MB)",
        data=gif,
        file_name=f"{file_stem}.gif",
        mime="image/gif",
    )
    if not loop:
        st.caption("Náhled se přehraje jednou. Pro nové přehrání stiskni v prohlížeči R (Rerun).")
