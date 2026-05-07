"""Tests for the velocity colormap."""
from __future__ import annotations

import pytest

# Importing the colormap requires PyQt5 (QColor); skip cleanly if absent
pytest.importorskip("PyQt5")

from disklavier_visualizer.ui.midi_canvas import _velocity_color


def _rgb(c):
    return (c.red(), c.green(), c.blue())


def test_velocity_0_is_blue():
    assert _rgb(_velocity_color(0)) == (60, 100, 200)


def test_velocity_64_is_green():
    assert _rgb(_velocity_color(64)) == (60, 200, 100)


def test_velocity_100_is_yellow():
    assert _rgb(_velocity_color(100)) == (255, 200, 50)


def test_velocity_127_is_red():
    assert _rgb(_velocity_color(127)) == (255, 60, 60)


def test_velocity_32_interpolates_between_blue_and_green():
    # halfway between (60,100,200) and (60,200,100)
    r, g, b = _rgb(_velocity_color(32))
    assert r == 60
    assert g == 150
    assert b == 150


def test_velocity_96_interpolates_between_green_and_yellow():
    # t = (96-64)/(100-64) = 32/36 ~= 0.8889
    # R = 60 + 0.8889*(255-60) = 60 + 173.33 = 233
    # G = 200 (both stops have g=200)
    # B = 100 + 0.8889*(50-100) = 100 - 44.44 = 55
    r, g, b = _rgb(_velocity_color(96))
    assert abs(r - 233) <= 1
    assert g == 200
    assert abs(b - 55) <= 1
