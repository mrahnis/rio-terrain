"""Test properties of a test raster against a reference raster."""

import time
import warnings

import click
import numpy as np
import rasterio

import rio_terrain as rt
import rio_terrain.tools.messages as msg

from rio_terrain import __version__ as plugin_version


@click.command('compare', short_help="Test properties of one raster against another.")
@click.argument('test_f', metavar='TEST', nargs=1, type=click.Path(exists=True))
@click.argument('reference_f', metavar='REFERENCE', nargs=1, type=click.Path(exists=True))
@click.option('--crs', is_flag=True, help="Compare CRS (Coordinate Reference System).")
@click.option('--transform', is_flag=True, help="Compare transform.")
@click.option('--bounds', is_flag=True, help="Compare data bounds.")
@click.option('--shape', is_flag=True, help="Compare shape in rows, columns.")
@click.option('--nans', is_flag=True, help="Test image nans for sameness.")
@click.option('--diff', is_flag=True, help="Test for image difference within tolerance.")
@click.option('--tolerance', nargs=1, default=0.1, help="Tolerance for difference comparision.")
@click.option('--all', 'test_all', is_flag=True, help="Run all tests.")
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=plugin_version, message='rio-channel v%(version)s')
@click.pass_context
def compare(ctx, test_f, reference_f, crs, transform, bounds, shape, nans, diff, tolerance, test_all, verbose):
    """Test properties of a TEST raster against a REFERENCE raster.

    \b
    TEST should be a single-band raster.
    REFERENCE should be a binary shape raster.

    \b
    Example:
    rio test test.tif reference.tif

    """
    if verbose:
        warnings.filterwarnings('default')
    else:
        warnings.filterwarnings('ignore')

    t0 = time.time()
    command = click.get_current_context().info_name

    if test_all:
        crs = transform = bounds = shape = nans = diff = True

    status = {}

    with rasterio.open(test_f) as test_src, rasterio.open(reference_f) as ref_src:

        if crs:
            if test_src.crs == ref_src.crs:
                status['crs'] = True
            else:
                status['crs'] = False
        if transform:
            if test_src.transform == ref_src.transform:
                status['transform'] = True
            else:
                status['transform'] = False
        if bounds:
            if test_src.bounds == ref_src.bounds:
                status['bounds'] = True
            else:
                status['bounds'] = False
        if shape:
            if test_src.shape == ref_src.shape:
                status['shape'] = True
            else:
                status['shape'] = False

        if any([nans, diff]):
            test_arr = test_src.read(1)
            ref_arr = ref_src.read(1)
            if nans:
                if np.all((test_arr == np.nan) == (ref_arr == np.nan)):
                    status['nans'] = True
                else:
                    status['nans'] = False
            if diff:
                err = test_arr - ref_arr
                if (np.absolute(err) < tolerance).all():
                    status['diff'] = True
                else:
                    status['diff'] = False

        for key, val in status.items():
            if val is True:
                click.echo(click.style('PASS', fg='green') + ": " + key)
            else:
                click.echo(click.style('FAIL', fg='red') + ": " + key)

    click.echo("Testing complete.")
    click.echo((msg.COMPLETION).format(msg.printtime(t0, time.time())))
