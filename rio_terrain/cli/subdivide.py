"""Extract separate raster files by zone polygon from a single raster."""

from __future__ import annotations

import os
import time
import warnings
from math import floor, ceil

import click
import numpy as np
import fiona
import rasterio
from rasterio import features
from rasterio.transform import from_bounds, from_origin
from shapely.geometry import shape, Polygon

import rio_terrain as rt
import rio_terrain.tools.messages as msg

from rio_terrain import __version__ as plugin_version


def to_raster(
    geom: Polygon,
    shape: tuple[int, int],
    transform: rasterio.Affine
) -> np.ndarray:
    """Rasterize geometries.

    Parameters:
        geom (Polygon)
        shape (tuple)
        transform (Affine)

    Returns:
        arr (ndarray)

    """
    arr = features.rasterize(
        [(geom, 1)],
        out_shape=shape,
        transform=transform,
        fill=0,
        dtype='uint8',
        all_touched=False,
    )
    return arr


@click.command('subdivide', short_help="Subdivide an image by polygons.")
@click.argument('input', nargs=1, type=click.Path(exists=True))
@click.argument('zones_f', metavar='ZONES', nargs=1, type=click.Path(exists=True))
@click.option(
    '--outdir', nargs=1, type=click.Path(exists=True, dir_okay=True, file_okay=False), default='.')
@click.option('--prefix', nargs=1, type=str, default='zone_')
@click.option('--zone-field', nargs=1, type=str, default=None)
@click.option('--buffer-distance', nargs=1, type=float, default=0.0)
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=plugin_version, message='rio-channel v%(version)s')
@click.pass_context
def subdivide(ctx, input, zones_f, outdir, prefix, zone_field, buffer_distance, verbose):
    """Extract separate raster files by zone polygon from a single raster.

    \b
    INPUT should be a single-band raster.
    ZONES should be a shapefile or geopackage of polygon geometries.

    \b
    Example:
    rio subdivide elevation.tif watersheds.shp --outdir results --prefix HUC_ --zone-field HUC6 --buffer-distance 1000

    """
    if verbose:
        warnings.filterwarnings('default')
    else:
        warnings.filterwarnings('ignore')

    t0 = time.time()
    command = click.get_current_context().info_name

    click.echo((msg.STARTING).format(command, input))

    with fiona.open(zones_f, 'r', encoding='utf-8') as zone_src, \
            rasterio.open(input, 'r') as src:

        block_shape = (src.block_shapes)[0]
        blockxsize = block_shape[1]
        blockysize = block_shape[0]

        i = 0
        for zone in zone_src:
            # start with a fresh profile for each zone
            profile = src.profile

            zone_buf = (shape(zone['geometry'])).buffer(buffer_distance)

            # dimensions of the zone raster
            _w, _s, _e, _n = zone_buf.bounds
            _ncols = int((ceil(_e) - floor(_w)) / src.res[0])
            _nrows = int((ceil(_n) - floor(_s)) / src.res[1])

            # intersection bounds of the zone raster and src
            w = np.maximum(floor(_w), src.bounds[0])
            s = np.maximum(floor(_s), src.bounds[1])
            e = np.minimum(ceil(_e), src.bounds[2])
            n = np.minimum(ceil(_n), src.bounds[3])

            # dimensions of the raster intersection
            ncols = int((e - w) / src.res[0])
            nrows = int((n - s) / src.res[1])
            # affine = from_bounds(w, s, e, n, ncols, nrows)
            affine = from_origin(w, n, src.res[0], src.res[1])
            col_start, row_start = ~src.transform * (w, n)

            read_windows = rt.tile_grid(
                ncols,
                nrows,
                blockxsize=blockxsize,
                blockysize=blockysize,
                col_offset=col_start,
                row_offset=row_start)
            write_windows = rt.tile_grid(
                ncols, nrows, blockxsize=blockxsize, blockysize=blockysize)

            mask = (to_raster(zone_buf, (_nrows, _ncols), affine)).astype(np.bool)

            # stripe the data if intersection is thin in one or more dimensions
            if (profile['blockxsize'] > ncols) or (profile['blockysize'] > nrows):
                profile.update(blockxsize=ncols, blockysize=1, tiled=False)

            profile.update(
                dtype=rasterio.float32,
                count=1,
                height=nrows,
                width=ncols,
                transform=affine,
                compress='deflate',
                predictor=3,
                bigtiff='yes')

            # write the zone to its own file
            if zone_field:
                filename = prefix + str(zone['properties'][zone_field]) + '.tif'
            else:
                filename = prefix + str(i) + '.tif'
            output = os.path.join(outdir, filename)
            with rasterio.open(output, 'w', **profile) as dst:
                for read_window, write_window in zip(read_windows, write_windows):
                    rows, cols = write_window.toslices()
                    data = src.read(1, window=read_window)
                    window_mask = (mask[rows, cols]).astype(np.float32)
                    window_mask[window_mask == 0] = np.nan
                    dst.write(data * window_mask, 1, window=write_window)
                i += 1

    click.echo('Wrote {} zones to {}'.format(i, outdir))
    click.echo((msg.COMPLETION).format(msg.printtime(t0, time.time())))
