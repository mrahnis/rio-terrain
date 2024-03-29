"""Calculate a level-of-detection raster."""

import time
import warnings
import concurrent.futures
from typing import Union

import click
import numpy as np
import rasterio

import rio_terrain as rt
import rio_terrain.tools.messages as msg
from rio_terrain import __version__ as plugin_version


def propagate(
    img0: np.ndarray,
    img1: np.ndarray,
    instrumental0: Union[int, float],
    instrumental1: Union[int, float]
) -> np.ndarray:
    """Propagate undertainty in addition or subtraction of two rasters.

    Parameters:
        img0: uncertainty raster
        img1: uncertainty raster
        instrumental0: instrumental or minumum uncertainty of img0
        instrumental1: instrumental or minumum uncertainty of img1

    Returns:
        propagated uncertainty raster

    """
    if instrumental0:
        img0[img0 < instrumental0] = instrumental0
    if instrumental1:
        img1[img1 < instrumental1] = instrumental1

    result = np.sqrt(np.square(img1) + np.square(img0))

    return result


@click.command('uncertainty', short_help="Calculate a level-of-detection raster.")
@click.argument('uncertainty0', nargs=1, type=click.Path(exists=True))
@click.argument('uncertainty1', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.option('--instrumental0', nargs=1, default=None, type=float,
              help='Minimum uncertainty for the first raster.')
@click.option('--instrumental1', nargs=1, default=None, type=float,
              help='Minimum uncertainty for the second raster.')
@click.option('-j', '--njobs', type=int, default=1, help='Number of concurrent jobs to run.')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=plugin_version, message='rio-terrain v%(version)s')
@click.pass_context
def uncertainty(
    ctx,
    uncertainty0,
    uncertainty1,
    output,
    instrumental0,
    instrumental1,
    njobs,
    verbose,
):
    """Calculate a level-of-detection raster.

    \b
    UNCERTAINTY0 should be a single-band raster for uncertainty at time 0.
    UNCERTAINTY1 should be a single-band raster for uncertainty at time 1.

    \b
    Example:
        rio uncertainty roughness_t0.tif roughness_t1.tif uncertainty.tif

    """
    if verbose:
        warnings.filterwarnings('default')
    else:
        warnings.filterwarnings('ignore')

    t0 = time.time()
    command = click.get_current_context().info_name

    with rasterio.open(uncertainty0) as src0, rasterio.open(uncertainty1) as src1:

        if not rt.is_raster_intersecting(src0, src1):
            raise ValueError(msg.NONINTERSECTING)
        if not rt.is_raster_aligned(src0, src1):
            # raise ValueError(msg.NONALIGNED)
            pass

        profile = src0.profile
        affine = src0.transform

        if njobs == 0:
            tiles = rt.tile_grid_intersection(src0, src1)
        else:            
            block_shape = (src0.block_shapes)[0]
            blockxsize = block_shape[1]
            blockysize = block_shape[0]
            tiles = rt.tile_grid_intersection(src0, src1, blockxsize=blockxsize, blockysize=blockysize)

        windows0, windows1, write_windows, affine, nrows, ncols = tiles

        profile.update(
            dtype=rasterio.float32,
            count=1,
            height=nrows,
            width=ncols,
            transform=affine,
            compress='deflate',
            predictor=3,
            bigtiff='yes',
        )

        with rasterio.open(output, 'w', **profile) as dst:
            if njobs ==0 or njobs == 1:
                if njobs == 0:
                    click.echo((msg.STARTING).format(command, msg.INMEMORY))
                else:
                    click.echo((msg.STARTING).format(command, msg.SEQUENTIAL))
                with click.progressbar(length=nrows * ncols, label='Blocks done:') as bar:
                    for (window0, window1, write_window) in zip(windows0, windows1, write_windows):
                        img0 = src0.read(1, window=window0)
                        img1 = src1.read(1, window=window1)
                        result = propagate(img0, img1, instrumental0, instrumental1)
                        dst.write(result.astype(profile['dtype']), 1, window=write_window)
                        bar.update(result.size)
            else:
                click.echo((msg.STARTING).format(command, msg.CONCURRENT))

                def jobs():
                    for (window0, window1, write_window) in zip(windows0, windows1, write_windows):
                        img0 = src0.read(1, window=window0)
                        img1 = src1.read(1, window=window1)
                        yield img0, img1, window0, window1, write_window

                with concurrent.futures.ThreadPoolExecutor(max_workers=njobs) as executor, \
                        click.progressbar(length=nrows * ncols, label='Blocks done:') as bar:

                    future_to_window = {
                        executor.submit(
                            propagate, img0, img1, instrumental0, instrumental1
                        ): (write_window)
                        for (img0, img1, window0, window1, write_window) in jobs()
                    }

                    for future in concurrent.futures.as_completed(future_to_window):
                        write_window = future_to_window[future]
                        result = future.result()
                        dst.write(result.astype(profile['dtype']), 1, window=write_window)
                        bar.update(result.size)

    click.echo((msg.WRITEOUT).format(output))
    click.echo((msg.COMPLETION).format(msg.printtime(t0, time.time())))
