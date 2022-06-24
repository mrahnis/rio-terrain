import pytest
# from hypothesis import given, assume, settings, HealthCheck
# from hypothesis.strategies import floats, integers

import numpy as np
from rasterio.windows import Window

import rio_terrain as rt


def test_tile_dim():
    # balance=False, merge=False, as_chunks=False/True
    assert np.array_equal(list(rt.tile_dim(20, 3)), [0, 3, 6, 9, 12, 15, 18])
    assert np.array_equal(list(rt.tile_dim(20, 3, as_chunks=True)), [3, 3, 3, 3, 3, 3, 2])

    # balance=False, merge=True, as_chunks=False/True
    assert np.array_equal(list(rt.tile_dim(20, 3, merge=True)), [0, 3, 6, 9, 12, 15])
    assert np.array_equal(list(rt.tile_dim(20, 3, merge=True, as_chunks=True)), [3, 3, 3, 3, 3, 5])

    # balance=True, merge=False, as_chunks=False/True
    assert np.array_equal(list(rt.tile_dim(200, 60, balance=True)), [0, 66, 132, 198])
    assert np.array_equal(list(rt.tile_dim(200, 60, balance=True, as_chunks=True)), [66, 66, 66, 2])

    # balance=True, merge=True, as_chunks=False/True
    assert np.array_equal(list(rt.tile_dim(200, 60, balance=True, merge=True)), [0, 66, 132])
    assert np.array_equal(list(rt.tile_dim(200, 60, balance=True, merge=True, as_chunks=True)), [66, 66, 68])


# input windows
ul_in_window = Window(col_off=10, row_off=10, width=128, height=128)
lr_in_window = Window(col_off=62, row_off=62, width=128, height=128)


def test_expand_window():
    ## test with upper-left window
    # expand window by margin within bounds
    ul_out_window = rt.expand_window(ul_in_window, src_shape=(200, 200), margin=5)
    assert (ul_out_window == Window(col_off=5, row_off=5, width=138, height=138))

    # expand window by margin at upper-left bound
    ul_out_window = rt.expand_window(ul_in_window, src_shape=(200, 200), margin=20)
    assert (ul_out_window == Window(col_off=0, row_off=0, width=158, height=158))

    # expand window by margin at lower-right bound
    lr_out_window = rt.expand_window(lr_in_window, src_shape=(200, 200), margin=20)
    assert (lr_out_window == Window(col_off=42, row_off=42, width=158, height=158))


def test_margins():
    # check margins within bounds
    assert (rt.margins(Window(col_off=5, row_off=5, width=138, height=138), ul_in_window) == (5, 5, 5, 5))

    # check margins at upper-left bounds
    assert (rt.margins(Window(col_off=0, row_off=0, width=158, height=158), ul_in_window) == (10, 10, 20, 20))

    # check margins at lower-right bounds
    assert (rt.margins(Window(col_off=42, row_off=42, width=158, height=158), lr_in_window) == (20, 20, 10, 10))


"""
def test_window_bounds():
    # todo: bounds coordinates from a window


def test_intersect_bounds():
    # todo: find intersection of two sets of bounds


def test_trim():
    # todo: trim the margins from a window


def test_tile_grid():
    # todo: tile a grid


def test_is_congruent():
    # todo: test for coincident bounds


def test_is_intersecting():
    # todo: test for bounds intersection


def test_is_aligned():
    # todo: test for cell alignment
"""