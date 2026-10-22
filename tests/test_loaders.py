"""Testy načítání exportů z Vensimu (model.loaders.load_vensim)."""

from pathlib import Path

import pandas as pd
import pytest

from model.loaders import data_report, load_vensim, time_window

DATA_DIR = Path(__file__).parent.parent / "data"
TRANSPOSED = DATA_DIR / "Shrinking time esc.txt"  # čas v prvním řádku
TIME_IN_ROWS = DATA_DIR / "SRINKING TIME.txt"  # čas v prvním sloupci
SINGLE_SERIES = DATA_DIR / "st_working effort.txt"


def test_both_orientations_give_same_data():
    """Stejná simulace exportovaná ve dvou orientacích musí dát shodný DataFrame."""
    pd.testing.assert_frame_equal(load_vensim(TRANSPOSED), load_vensim(TIME_IN_ROWS))


def test_time_is_float_index():
    df = load_vensim(TIME_IN_ROWS)
    assert df.index.name == "Time (Day)"
    assert df.index.dtype == "float64"
    assert df.index[0] == 0
    assert df.index.is_monotonic_increasing  # čas musí růst


def test_columns_without_suffix_and_empty_columns():
    """Přípona " : current" je pryč a prázdný sloupec z tabulátoru na konci řádku zahozen."""
    df = load_vensim(TIME_IN_ROWS)
    assert df.columns.tolist() == ["progress", "Work done", "Work to do"]
    assert not df.isna().any().any()


def test_single_series():
    df = load_vensim(SINGLE_SERIES)
    assert df.columns.tolist() == ["Working effort"]
    assert len(df) == 801


def test_file_like_object():
    """Streamlit předává nahraný soubor jako objekt v paměti, ne jako cestu."""
    with open(TIME_IN_ROWS, "rb") as f:
        df = load_vensim(f)
    assert df.columns.tolist() == ["progress", "Work done", "Work to do"]


def test_wrong_separator_raises(tmp_path):
    """tmp_path = dočasná složka, kterou pytest vytvoří pro každý test zvlášť."""
    bad_file = tmp_path / "bad.csv"
    bad_file.write_text("Time (Day),progress\n0,2\n1,3\n")  # čárky místo tabulátorů
    with pytest.raises(ValueError, match="málo řádků nebo sloupců"):
        load_vensim(bad_file)


def test_non_numeric_values_raise(tmp_path):
    bad_file = tmp_path / "bad.txt"
    bad_file.write_text("Time (Day)\tprogress\n0\t2\n1\tabc\n")
    with pytest.raises(ValueError, match="nečíselné hodnoty"):
        load_vensim(bad_file)


# --- time_window ---


def test_time_window_includes_edges():
    df = load_vensim(TIME_IN_ROWS)
    window = time_window(df, 10, 20)
    assert window.index[0] == 10
    assert window.index[-1] == 20
    assert len(window) == 81  # 10 dní po 0.125 = 80 kroků + kraj


def test_time_window_float_tolerance():
    """Hranice spočítaná s nepřesností desetinných čísel (0.1 + 0.2) nesmí kraj vynechat."""
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0]}, index=[0.0, 0.3, 0.6])
    assert len(time_window(df, 0.1 + 0.2, 0.6)) == 2


def test_time_window_wrong_order():
    df = load_vensim(TIME_IN_ROWS)
    with pytest.raises(ValueError):
        time_window(df, 20, 10)


# --- data_report ---


def test_data_report_real_file():
    report = data_report(load_vensim(TIME_IN_ROWS))
    assert report["rows"] == 801
    assert report["series"] == ["progress", "Work done", "Work to do"]
    assert report["time_start"] == 0
    assert report["time_end"] == 100
    assert report["time_step"] == 0.125
    assert report["time_increasing"]
    assert report["missing"] == {}


def test_data_report_missing_values(tmp_path):
    """Prázdná buňka uprostřed dat se má objevit v přehledu chybějících hodnot."""
    file = tmp_path / "gaps.txt"
    file.write_text("Time (Day)\ta\tb\n0\t1\t5\n1\t\t6\n2\t3\t7\n")
    report = data_report(load_vensim(file))
    assert report["missing"] == {"a": 1}


def test_data_report_single_row(tmp_path):
    file = tmp_path / "one.txt"
    file.write_text("Time (Day)\ta\n0\t1\n")
    assert data_report(load_vensim(file))["time_step"] is None
