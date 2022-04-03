import pytest
from collections import namedtuple

import numpy as np
import rasterio
from rasterio.rio.main import main_group


testdem = 'rio_terrain/tests/data/dem_100m.tif'
Tolerances = namedtuple('Tolerances', 'max mean std')


def test_slope_n8_deg(tmpdir, runner):
    outfile = str(tmpdir.join('out.tif'))
    reffile = 'rio_terrain/tests/data/ref_gdal_slope_degrees_100m.tif'
    result = runner.invoke(main_group, ['slope', testdem, outfile, '--neighbors', '8', '--units', 'degrees', '-j', '0'], catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src, rasterio.open(reffile) as ref:
        assert src.count == 1
        assert src.meta['dtype'] == 'float32'
        arr = src.read(1)
        refarr = ref.read(1)
        err = refarr[1:-1, 1:-1] - arr[1:-1, 1:-1]
        print('Max err:', np.absolute(err).max())
        print('Mean err:', err.mean())
        print('Std err:', err.std())
        tol = Tolerances(max=0.1, mean=0.01, std=0.1)
        assert (np.absolute(err) < tol.max).all()
        assert np.absolute(err.mean()) < tol.mean
        assert err.std() < tol.std


def test_slope_n8_grade(tmpdir, runner):
    outfile = str(tmpdir.join('out.tif'))
    reffile = 'rio_terrain/tests/data/ref_gdal_slope_percent_100m.tif'
    result = runner.invoke(main_group, ['slope', testdem, outfile, '--neighbors', '8', '--units', 'grade', '-j', '0'], catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src, rasterio.open(reffile) as ref:
        assert src.count == 1
        assert src.meta['dtype'] == 'float32'
        arr = src.read(1)
        refarr = ref.read(1)
        err = refarr[1:-1, 1:-1]/100 - arr[1:-1, 1:-1]
        print('Max err:', np.absolute(err).max())
        print('Mean err:', err.mean())
        print('Std err:', err.std())
        tol = Tolerances(max=0.002, mean=0.0001, std=0.001)
        assert (np.absolute(err) < tol.max).all()
        assert np.absolute(err.mean()) < tol.mean
        assert err.std() < tol.std


def test_aspect_n8_azimuth(tmpdir, runner):
    outfile = str(tmpdir.join('out.tif'))
    reffile = 'rio_terrain/tests/data/ref_gdal_aspect_azim_100m.tif'
    result = runner.invoke(main_group, ['aspect', testdem, outfile, '--neighbors', '8', '--pcs', 'compass', '-j', '0'], catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src, rasterio.open(reffile) as ref:
        assert src.count == 1
        assert src.meta['dtype'] == 'float32'
        arr = src.read(1)
        refarr = ref.read(1)
        err_tmp = np.absolute(refarr[1:-1, 1:-1] - arr[1:-1, 1:-1])
        err = np.minimum(err_tmp, 360 - err_tmp)
        print('Max err:', err.max())
        print('Mean err:', err.mean())
        print('Std err:', err.std())
        tol = Tolerances(max=1, mean=0.01, std=0.01)
        assert (err < tol.max).all()
        assert err.mean() < tol.mean
        assert err.std() < tol.std


def test_aspect_n8_cartesian(tmpdir, runner):
    outfile = str(tmpdir.join('out.tif'))
    reffile = 'rio_terrain/tests/data/ref_gdal_aspect_trig_100m.tif'
    result = runner.invoke(main_group, ['aspect', testdem, outfile, '--neighbors', '8', '--pcs', 'cartesian', '-j', '0'], catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src, rasterio.open(reffile) as ref:
        assert src.count == 1
        assert src.meta['dtype'] == 'float32'
        arr = src.read(1)
        refarr = ref.read(1)
        err_tmp = np.absolute(refarr[1:-1, 1:-1] - arr[1:-1, 1:-1])
        err = np.minimum(err_tmp, 360 - err_tmp)
        print('Max err:', err.max())
        print('Mean err:', err.mean())
        print('Std err:', err.std())
        tol = Tolerances(max=1, mean=0.01, std=0.01)
        assert (err < tol.max).all()
        assert err.mean() < tol.mean
        assert err.std() < tol.std

def test_curvature_n4(tmpdir, runner):
    outfile = str(tmpdir.join('out.tif'))
    reffile = 'rio_terrain/tests/data/ref_richdem_curvature_total_100m.tif'
    result = runner.invoke(main_group, ['curvature', testdem, outfile, '--neighbors', '4', '-j', '0'], catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src, rasterio.open(reffile) as ref:
        assert src.count == 1
        assert src.meta['dtype'] == 'float32'
        arr = src.read(1)
        refarr = ref.read(1)
        err = refarr[1:-1, 1:-1]/100 - arr[1:-1, 1:-1]
        print('Max err:', np.absolute(err).max())
        print('Mean err:', err.mean())
        print('Std err:', err.std())
        tol = Tolerances(max=0.1, mean=0.01, std=0.02)
        assert (np.absolute(err) < tol.max).all()
        assert np.absolute(err.mean()) < tol.mean
        assert err.std() < tol.std

