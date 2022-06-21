"""Set values of one raster to nodata based on another"""

import time
import warnings
import concurrent.futures
import multiprocessing
from typing import Union

import click
import numpy as np
import rasterio

import rio_terrain as rt
import rio_terrain.tools.messages as msg
from rio_terrain.tools.numbers import is_all_nan, nan_shape

from rio_terrain import __version__ as plugin_version


def do_copynodata(
    intensity: np.ndarray,
    mask: np.ndarray,
    nodata: Union[int, float],
    mask_nodata: Union[int, float]
) -> np.ndarray:
    result = np.where((np.isnan(mask)), nodata, intensity)
    return result


@click.command('copynodata', short_help="Transfer nodata from one raster to another.")
@click.argument('intensity_f', metavar='INTENSITY', nargs=1, type=click.Path(exists=True))
@click.argument('mask_f', metavar='MASK', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.option('-b', '--blocks', 'blocks', nargs=1, type=int, default=40,
              help='Multiply TIFF block size by an amount to make chunks')
@click.option('-j', '--jobs', 'njobs', type=int, default=1,
              help='Number of concurrent jobs to run')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=plugin_version, message='rio-channel v%(version)s')
@click.pass_context
def copynodata(ctx, intensity_f, mask_f, output, blocks, njobs, verbose):
    """Stamp one single-band raster into another.

    \b
    INTENSITY should be a single-band raster.
    MASK should be a single-band raster.

    \b
    Example:
    rio copynodata elevation.tif voids.tif fixed.tif

    """
    if verbose:
        np.warnings.filterwarnings('default')
    else:
        np.warnings.filterwarnings('ignore')

    t0 = time.time()
    command = click.get_current_context().info_name

    with rasterio.open(intensity_f) as intensity_src, rasterio.open(mask_f) as mask_src:
        profile = intensity_src.profile

        if profile['dtype'] in ['uint8', 'int32']:
            nodata = np.iinfo(np.int32).min
            profile.update(
                dtype=rasterio.int32,
                nodata=nodata,
                count=1,
                compress='lzw',
                bigtiff='YES')
        elif profile['dtype'] in ['float32', 'float64']:
            nodata = np.finfo(np.float32).min
            profile.update(
                dtype=rasterio.float32,
                nodata=nodata,
                count=1,
                compress='lzw',
                bigtiff='YES')
        else:
            click.echo('No change in profile')

        blockshape = (list(intensity_src.block_shapes))[0]
        if njobs == 0:
            w, s, e, n = intensity_src.bounds
            full_window = rasterio.windows.from_bounds(w, s, e, n, transform=src.transform)
            read_windows = [full_window]
            write_windows = [full_window]
        else:
            if intensity_src.is_tiled:
                if (blockshape[0] == 1) or (blockshape[1] == 1):
                    warnings.warn((msg.STRIPED).format(blockshape))
            else:
                blockshape = [128, 128]
                warnings.warn((msg.NOTILING).format(intensity_src.shape))

            windows = rt.tile_grid(
                intensity_src.width,
                intensity_src.height,
                blockshape[0]*blocks,
                blockshape[1]*blocks,
                overlap=0)

        with rasterio.open(output, 'w', **profile) as dst:
            if njobs == 0 or njobs == 1:
                if njobs == 0:
                    click.echo((msg.STARTING).format(command, msg.INMEMORY))
                else:
                    click.echo((msg.STARTING).format(command, msg.SEQUENTIAL))
                with click.progressbar(
                        length=intensity_src.height*intensity_src.width,
                        label='Blocks done:') as bar:
                    for window in windows:
                        intensity = intensity_src.read(1, window=window)
                        mask = mask_src.read(1, window=window)
                        result = do_copynodata(intensity.astype(profile['dtype']), mask, nodata, mask_src.nodata)
                        dst.write(result.astype(profile['dtype']), 1, window=window)
                        bar.update(result.size)
            else:
                click.echo((msg.STARTING).format(command, msg.CONCURRENT))

                def jobs():
                    for (ij, window) in intensity_src.block_windows():
                        intensity = intensity_src.read(1, window=window)
                        mask = mask_src.read(1, window=window)
                        yield intensity, mask, window

                with concurrent.futures.ThreadPoolExecutor(max_workers=njobs) as executor, \
                        click.progressbar(
                            length=intensity_src.width*intensity_src.height,
                            label='Blocks done:') as bar:

                    future_to_window = {
                        executor.submit(
                            do_copynodata, intensity, mask, nodata, mask_src.nodata
                        ): (window)
                        for (intensity, mask, window) in jobs()
                    }

                    for future in concurrent.futures.as_completed(future_to_window):
                        window = future_to_window[future]
                        result = future.result()
                        dst.write(result.astype(profile['dtype']), 1, window=window)
                        bar.update(result.size)

                """
                import dask.array as da

                with click.progressbar(
                        length=intensity_src.width*intensity_src.height,
                        label='Blocks done:') as bar:
                    for window in windows:
                        intensity = intensity_src.read(1, window=window)
                        mask = mask_src.read(1, window=window)

                        hh, ww = rt.tile_dims(
                            (intensity.shape[0], intensity.shape[1]),
                            (blockshape[0] * 4, blockshape[1] * 4),
                            min_size=blockshape[0] * 2,
                            balance=True,
                            merge=True,
                            as_chunks=True)

                        result = da.map_overlap(
                            do_copynodata,
                            intensity=intensity.astype(profile['dtype']),
                            dtype=profile['dtype'],
                            mask=mask,
                            nodata=nodata,
                            mask_nodata=mask_src.nodata,
                            boundary='reflect').compute()

                        dst.write(result.astype(profile['dtype']), 1, window=window)
                        bar.update(result.size)
                """

    click.echo((msg.WRITEOUT).format(output))
    click.echo((msg.COMPLETION).format(msg.printtime(t0, time.time())))
