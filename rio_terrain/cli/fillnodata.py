"""Apply hysteresis thresholding to a raster."""

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


def do_fillnodata(
    intensity: np.ndarray,
    mask: np.ndarray = None,
    max_search_distance: float = 100.0,
    smoothing_iterations: int = 0,
    nodata: Union[None, int, float] = None
) -> np.ndarray:
    """Fill nodata

    Parameters:
        intensity (ndarray)
        mask
        max_search_distance
        smoothing_iterations
        nodata (int or float)

    """
    if mask is None:
        # mask = np.where((np.isnan(intensity)), 0, 1)
        mask = np.where((intensity == nodata), 0, 1)

    if 0 < np.count_nonzero(mask) < intensity.size:
        result = rasterio.fill.fillnodata(
            intensity,
            mask=mask,
            max_search_distance=max_search_distance,
            smoothing_iterations=smoothing_iterations
        )
    else:
        result = intensity

    return result


@click.command('fillnodata', short_help="Fill nodate cells by interpolation.")
@click.argument('input', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.option('--mask', 'mask_f', nargs=1, type=click.Path(), help="Mask containing cells to fill")
@click.option('-d', '--distance', nargs=1, type=float, default=100.0, help="Maximum search distance")
@click.option('-n', '--iterations', nargs=1, type=int, default=0, help="Number of smoothing iterations")
@click.option('-j', '--njobs', type=int, default=1,
              help="Number of concurrent jobs to run.")
@click.option('-v', '--verbose', is_flag=True, help="Enables verbose mode.")
@click.version_option(version=plugin_version, message="rio-terrain v%(version)s")
@click.pass_context
def fillnodata(ctx, input, output, mask_f, distance, iterations, njobs, verbose):
    """Fill nodata cells by interpolation.

    INPUT should be a single-band continuous raster.

    \b
    Example:
    rio fillnodata holes.tif noholes.tif

    """
    if verbose:
        np.warnings.filterwarnings('default')
    else:
        np.warnings.filterwarnings('ignore')

    t0 = time.time()
    command = click.get_current_context().info_name

    with rasterio.open(input) as src
        if mask_f:
            mask_src = rasterio.open(mask_f)

        profile = src.profile
        affine = src.transform

        # nodata = np.finfo(np.float32).min
        nodata = profile['nodata']
        profile.update(
            dtype=rasterio.float32,
            count=1,
            compress='deflate',
            predictor=3,
            bigtiff='YES')

        if njobs == 0:
            w, s, e, n = src.bounds
            full_window = rasterio.windows.from_bounds(w, s, e, n, transform=src.transform)
            read_windows = [full_window]
            write_windows = [full_window]
        else: 
            if src.is_tiled:
                blockshape = (list(src.block_shapes))[0]
                if (blockshape[0] == 1) or (blockshape[1] == 1):
                    warnings.warn((msg.STRIPED).format(blockshape))
            else:
                blockshape = [128, 128]
                warnings.warn((msg.NOTILING).format(src.shape))
            read_windows = rt.tile_grid(
                src.width,
                src.height,
                blockshape[0],
                blockshape[1],
                overlap=distance)
            write_windows = rt.tile_grid(
                src.width,
                src.height,
                blockshape[0],
                blockshape[1],
                overlap=0)

        with rasterio.open(output, 'w', **profile) as dst:
            if njobs == 0 or njobs == 1:
                if njobs == 0:
                    click.echo((msg.STARTING).format(command, msg.INMEMORY))
                else:
                    click.echo((msg.STARTING).format(command, msg.SEQUENTIAL))
                with click.progressbar(length=src.width*src.height, label="Blocks done:") as bar:
                    for read_window, write_window in zip(read_windows, write_windows):
                        intensity = src.read(1, window=read_window)
                        mask = mask_src.read(1, window=read_window)
                        full_result = do_fillnodata(intensity, mask, distance, iterations, nodata)
                        result = rt.trim(full_result, rt.margins(read_window, write_window))
                        dst.write(result.astype(profile['dtype']), 1, window=write_window)
                        bar.update(result.size)
            else:
                click.echo((msg.STARTING).format(command, msg.CONCURRENT))

                def jobs():
                    for (read_window, write_window) in zip(read_windows, write_windows):
                        intensity = src.read(1, window=read_window)
                        mask = mask_src.read(1, window=read_window)
                        yield intensity, mask, read_window, write_window

                with concurrent.futures.ThreadPoolExecutor(max_workers=njobs) as executor, \
                        click.progressbar(length=src.width*src.height, label="Blocks done:") as bar:

                    future_to_window = {
                        executor.submit(
                            do_fillnodata, intensity, mask, distance, iterations, nodata
                        ): (read_window, write_window)
                        for (intensity, mask, read_window, write_window) in jobs()
                    }

                    for future in concurrent.futures.as_completed(future_to_window):
                        read_window, write_window = future_to_window[future]
                        full_result = future.result()
                        result = rt.trim(full_result, rt.margins(read_window, write_window))
                        dst.write(result.astype(profile['dtype']), 1, window=write_window)
                        bar.update(result.size)
        mask_src.close()
    click.echo((msg.WRITEOUT).format(output))
    click.echo((msg.COMPLETION).format(msg.printtime(t0, time.time())))
