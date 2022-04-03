"""Calculate coordinate bounds from labeled skeleton components."""

from __future__ import annotations

import sys
import time
import warnings
import math
from typing import Union, Any

import click
import numpy as np
from scipy import ndimage
import rasterio
from rasterio.windows import Window
from rasterio import transform
import fiona
from shapely.geometry import box, mapping

import rio_terrain as rt
import rio_terrain.tools.messages as msg

from rio_terrain import __version__ as plugin_version


schema = {
    'geometry': 'Polygon',
    'properties': {
        'id': 'int',
        'min': 'float',
        'max': 'float'
    },
}


def slices_to_windows(
    slices: list[tuple[slice, slice]]
) -> tuple[list[Window], list[Any]]:
    """Create a list of labels and windows

    Parameters:
        slices (list) : list of labels and slices output of ndimage.find_objects

    Returns:
        windows (list) : list of raster Windows labels (list) : list of integer labels

    """
    windows = []
    labels = []
    for label, islice in enumerate(slices):
        if islice:
            try:
                slicex = slice(islice[0].start, islice[0].stop, 1)
                slicey = slice(islice[1].start, islice[1].stop, 1)
                window = Window.from_slices(slicex, slicey)
                windows.append(window)
                labels.append(label)
            except (ValueError) as err:
                warnings.warn(str(err))
                pass

    return windows, labels


def do_shape_intensity(
    intensities: dict[str, list[Any]],
    skeleton: np.ndarray,
    intensity: np.ndarray
) -> dict[str, list[Any]]:
    """Maintain a dictionary of skeleton component minumum intensity.

    Parameters:
        intensities (dict) : keys are shape labels, values are minimum 
        skeleton (ndarray) : labeled shapes raster
        intensity (ndarray) : intensity raster

    Returns:
        intensities (dict) : dictionary of minimum raster intensity

    """
    for label in np.unique(skeleton):
        tmp_min = np.nanmin(intensity[skeleton == label])
        tmp_max = np.nanmax(intensity[skeleton == label])
        if label in intensities:
            intensities[label] = [np.minimum(tmp_min, (intensities[label])[0]),
                                  np.maximum(tmp_max, (intensities[label])[1])]
        else:
            intensities[label] = [tmp_min, tmp_max]

    return intensities


def do_shape_windows(bounds, shapes, read_window=None):
    """Maintain a dict of labeled shape bounds.

    Parameters:
        bounds (dict) : keys are shape labels, values are windows
        shapes (ndarray) : labeled shapes raster
        read_window (Window) : ndarray window within the data source

    Returns:
        bounds (dict) : dictionary of shape raster windows
    """

    slices = ndimage.find_objects(shapes)
    windows, labels = slices_to_windows(slices)

    if read_window:
        read_row_off = read_window.row_off
        read_col_off = read_window.col_off
    else:
        read_row_off = 0
        read_col_off = 0

    for label, window in zip(labels, windows):

        window = Window(
            window.col_off + read_col_off,
            window.row_off + read_row_off,
            window.width,
            window.height)

        if label in bounds:
            bounds[label] = rasterio.windows.union(bounds[label], window)
        else:
            bounds[label] = window

    return bounds


@click.command('labelbounds', short_help="Calculate coordinate bounding boxes from labeled skeleton components.")
@click.argument('skeleton_f', metavar='SKELETON', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.option('--intensity', 'intensity_f', nargs=1, type=click.Path(exists=True),
              help="Grayscale intensity image.")
@click.option('-b', '--blocks', 'blocks', nargs=1, type=int, default=40,
              help='Multiply TIFF block size by an amount to make chunks')
@click.option('-j', '--jobs', 'njobs', type=int, default=1,
              help='Number of concurrent jobs to run')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=plugin_version, message='rio-channel v%(version)s')
@click.pass_context
def labelbounds(ctx, skeleton_f, output, intensity_f, blocks, njobs, verbose):
    """Calculate coordinate bounding boxes from labeled SKELETON components.

    \b
    SKELETON should be a labeled shape raster.

    \b
    Example:
    rio labelbounds labeled_skeleton.tif bboxes.shp --intensity elevation.tif

    """
    if verbose:
        np.warnings.filterwarnings('default')
    else:
        np.warnings.filterwarnings('ignore')

    t0 = time.time()
    command = click.get_current_context().info_name

    if output.endswith('.shp'):
        driver = 'ESRI Shapefile'
    elif output.endswith('.gpkg'):
        driver = 'GPKG'
    else:
        click.UsageError("Only writing GeoPackage and shapefile currently")

    with rasterio.open(skeleton_f) as skeleton_src:

        if intensity_f:
            intensity_src = rasterio.open(intensity_f, 'r')

        if njobs >= 1:
            blockshape = (list(skeleton_src.block_shapes))[0]
            if (blockshape[0] == 1) or (blockshape[1] == 1):
                warnings.warn((msg.STRIPED).format(blockshape))
            read_windows = rt.tile_grid(
                skeleton_src.width,
                skeleton_src.height,
                blockshape[0]*blocks,
                blockshape[1]*blocks,
                overlap=0)

        label_windows = {}
        label_intensities = {}

        if njobs < 1:
            click.echo((msg.STARTING).format(command, msg.INMEMORY))
            skeleton = skeleton_src.read(1)
            if intensity_f:
                intensity = intensity_src.read(1)
                intensity[intensity <= intensity_src.nodata+1] = np.nan
                label_intensities = do_shape_intensity(label_intensities, skeleton, intensity)
            label_windows = do_shape_windows(label_windows, skeleton)
        elif njobs == 1:
            click.echo((msg.STARTING).format(command, msg.SEQUENTIAL))

            with click.progressbar(
                    length=skeleton_src.height*skeleton_src.width,
                    label='Blocks done:') as bar:
                for read_window in read_windows:
                    skeleton = skeleton_src.read(1, window=read_window)
                    if intensity_f:
                        intensity = intensity_src.read(1, window=read_window)
                        intensity[intensity <= intensity_src.nodata+1] = np.nan
                        label_intensities = do_shape_intensity(label_intensities, skeleton, intensity)
                    label_windows = do_shape_windows(label_windows, skeleton, read_window=read_window)
                    bar.update(skeleton.size)
        else:
            click.echo((msg.STARTING).format(command, msg.CONCURRENT))
            sys.exit('Concurrent not implemented, exiting now.')

        # write out
        with fiona.open(output, 'w', driver=driver, crs=skeleton_src.crs, schema=schema) as dst:
            for key, window in label_windows.items():
                bbox = rasterio.windows.bounds(window, skeleton_src.transform)
                geom = box(*bbox)
                if key in label_intensities:
                    vals = label_intensities[key]
                else:
                    vals = [np.nan, np.nan]
                dst.write({
                    'geometry': mapping(geom),
                    'properties': {
                        'id': key,
                        'min': float(vals[0]),
                        'max': float(vals[1])
                    }
                })

    click.echo('Wrote {} bounding boxes to {}'.format(len(label_windows), output))
    click.echo((msg.COMPLETION).format(msg.printtime(t0, time.time())))
