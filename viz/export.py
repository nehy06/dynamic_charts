"""Export grafů do GIF a PNG.

Funkce vrací bajty (pro st.image a st.download_button), nic neukládají do projektu.
"""

import tempfile
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.figure import Figure

from viz.animation import DEFAULT_FPS

DPI = 100
DPI_OPTIONS = {"Standardní (100 DPI)": 100, "Ostřejší (150 DPI)": 150, "Vysoká (200 DPI)": 200}
MAX_SIZE_MB = 5  # nad tuto velikost souboru uživatele upozorníme

# PillowWriter drží všechny snímky v paměti až do uložení; Streamlit Community Cloud
# má omezenou paměť, proto generování nad tento odhad nepustíme
MAX_MEMORY_MB = 800


def estimate_memory_mb(
    n_frames: int, figsize: tuple[float, float], dpi: int, transparent: bool = False
) -> float:
    """Odhadne paměť na snímky animace v MB (šířka × výška v pixelech × bajty na pixel).

    Neprůhledné snímky se ukládají jako RGB (3 B na pixel), průhledné jako RGBA (4 B).
    """
    width_px, height_px = figsize[0] * dpi, figsize[1] * dpi
    bytes_per_pixel = 4 if transparent else 3
    return n_frames * width_px * height_px * bytes_per_pixel / 1e6


class PillowWriterNoLoop(PillowWriter):
    """PillowWriter, který uloží GIF bez smyčky.

    Původní PillowWriter má natvrdo loop=0 (nekonečná smyčka). Když parametr loop
    vůbec nepředáme, Pillow informaci o opakování do GIFu nezapíše -> animace se
    přehraje jednou a zůstane stát na posledním snímku (hotový graf).
    Pozor: přepisuje metodu, která pracuje s interním atributem _frames - po
    aktualizaci matplotlibu ověř testem test_gif_plays_once.
    """

    def finish(self):
        self._frames[0].save(
            self.outfile,
            save_all=True,
            append_images=self._frames[1:],
            duration=int(1000 / self.fps),
        )


def export_gif(
    ani: FuncAnimation,
    fps: int = DEFAULT_FPS,
    loop: bool = False,
    dpi: int = DPI,
    progress_callback: Callable[[int, int], None] | None = None,
) -> bytes:
    """Vyrenderuje animaci do GIFu a vrátí jeho obsah.

    Args:
        ani: animace z viz.animation.animated_chart.
        fps: snímků za sekundu.
        loop: False = přehraje se jednou a zůstane na posledním snímku, True = smyčka.
        dpi: rozlišení snímků.
        progress_callback: volá se po každém snímku jako f(číslo_snímku, celkem_snímků),
            např. pro st.progress.
    """
    writer = PillowWriter(fps=fps) if loop else PillowWriterNoLoop(fps=fps)
    # matplotlib ukládá animaci do souboru -> dočasná složka, která po bloku zmizí
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "animation.gif"
        ani.save(path, writer=writer, dpi=dpi, progress_callback=progress_callback)
        return path.read_bytes()


def export_png(fig: Figure, dpi: int = DPI) -> bytes:
    """Uloží statický graf do PNG a vrátí jeho obsah."""
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=dpi)
    return buffer.getvalue()


def size_mb(data: bytes) -> float:
    """Velikost exportovaného souboru v MB."""
    return len(data) / 1e6
