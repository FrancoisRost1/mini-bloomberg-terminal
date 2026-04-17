"""Debug gate for the per section data source watermarks.

The 2026-04-17 audit flagged the "SRC YFINANCE" labels on every chart
header as noise for external visitors. They remain useful for internal
debugging, so they are toggled by ``config.yaml`` ``app.debug``. These
tests lock the default-off behavior and the setter contract so the
watermarks can never silently re-appear on prod.
"""

from __future__ import annotations

from terminal.utils.density import section_bar, set_show_data_sources, show_data_sources
from terminal.utils.error_handling import inline_status_line, data_status


def test_section_bar_hides_source_by_default():
    set_show_data_sources(False)
    html = section_bar("GLOBAL INDICES", source="yfinance")
    assert "SRC YFINANCE" not in html
    assert "GLOBAL INDICES" in html


def test_section_bar_shows_source_when_debug_enabled():
    set_show_data_sources(True)
    try:
        html = section_bar("GLOBAL INDICES", source="yfinance")
        assert "SRC YFINANCE" in html
    finally:
        set_show_data_sources(False)


def test_inline_status_line_hides_source_by_default():
    set_show_data_sources(False)
    html = inline_status_line("OFF", source="yfinance")
    assert "SRC YFINANCE" not in html
    assert "DATA OFF" in html


def test_inline_status_line_shows_source_when_debug_enabled():
    set_show_data_sources(True)
    try:
        html = inline_status_line("PARTIAL", source="FRED")
        assert "SRC FRED" in html
    finally:
        set_show_data_sources(False)


def test_data_status_respects_debug_gate():
    set_show_data_sources(False)
    assert "SRC " not in data_status("LIVE", source="yfinance")
    set_show_data_sources(True)
    try:
        assert "SRC YFINANCE" in data_status("LIVE", source="yfinance")
    finally:
        set_show_data_sources(False)


def test_show_data_sources_reflects_setter():
    set_show_data_sources(True)
    assert show_data_sources() is True
    set_show_data_sources(False)
    assert show_data_sources() is False
