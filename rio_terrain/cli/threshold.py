import time
import warnings
import concurrent.futures
import multiprocessing

import click
import numpy as np
import rasterio

import rio_terrain as rt
import rio_terrain.tools.messages as msg
from rio_terrain import __version__ as plugin_version


def _thresh(data0, data1, level, default=0):
    conditions = [data0 >= data1*level, data0 <= -data1*level]
    choices = [1, -1]
    result = np.select(conditions, choices, default=default)
    return result


@click.command()
@click.argument('input', nargs=1, type=click.Path(exists=True))
@click.argument('uncertainty', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.argument('level', nargs=1, type=float)
@click.option('-j', '--njobs', type=int, default=multiprocessing.cpu_count(),
              help='Number of concurrent jobs to run.')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=plugin_version, message='rio-terrain v%(version)s')
@click.pass_context
def threshold(ctx, input, uncertainty, output, level, njobs, verbose):
    """Thresholds a raster based on an uncertainty raster.

    \b
    Example:
    rio threshold diff.tif uncertainty.tif, detected.tif 1.68

    """
    if verbose:
        np.warnings.filterwarnings('default')
    else:
        np.warnings.filterwarnings('ignore')

    t0 = time.time()

    with rasterio.Env():

        with rasterio.open(input) as src0, \
                rasterio.open(uncertainty) as src1:

            if not rt.is_raster_intersecting(src0, src1):
                raise ValueError(msg.NONINTERSECTING)
            if not rt.is_raster_aligned(src0, src1):
                raise ValueError(msg.NONALIGNED)

            profile = src0.profile
            affine = src0.transform
            step = (affine[0], affine[4])
            nodata = np.iinfo(np.int32).min

            if njobs >= 1:
                block_shape = (src0.block_shapes)[0]
                blockxsize = block_shape[1]
                blockysize = block_shape[0]
            else:
                blockxsize = None
                blockysize = None

            tiles = rt.tile_grid_intersection(src0, src1, blockxsize=blockxsize, blockysize=blockysize)
            windows0, windows1, write_windows, affine, nrows, ncols = tiles

            profile.update(dtype=rasterio.int32, nodata=nodata, count=1,
                           height=nrows, width=ncols, transform=affine,
                           compress='lzw', bigtiff='yes')

            with rasterio.open(output, 'w', **profile) as dst:
                if njobs < 1:
                    click.echo((msg.STARTING).format('threshold', msg.INMEMORY))
                    data0 = src0.read(1, window=next(windows0))
                    data1 = src1.read(1, window=next(windows1))
                    result = _thresh(data0, data1, level, default=nodata)
                    dst.write(result, 1)
                elif njobs == 1:
                    click.echo((msg.STARTING).format('threshold', msg.SEQUENTIAL))
                    with click.progressbar(length=nrows*ncols, label='Blocks done:') as bar:
                        for (window0, window1, write_window) in zip(windows0, windows1, write_windows):
                            data0 = src0.read(1, window=window0)
                            data1 = src1.read(1, window=window1)
                            result = _thresh(data0, data1, level, default=nodata)
                            dst.write(result, 1, window=write_window)
                            bar.update(result.size)
                else:
                    click.echo((msg.STARTING).format('threshold', msg.CONCURRENT))

                    def jobs():
                        for (window0, window1, write_window) in zip(windows0, windows1, write_windows):
                            data0 = src0.read(1, window=window0)
                            data1 = src1.read(1, window=window1)
                            yield data0, data1, window0, window1, write_window

                    with concurrent.futures.ThreadPoolExecutor(max_workers=njobs) as executor, \
                            click.progressbar(length=nrows*ncols, label='Blocks done:') as bar:

                        future_to_window = {
                            executor.submit(
                                _thresh,
                                data0,
                                data1,
                                level,
                                default=nodata): (window0, window1, write_window)
                            for (data0, data1, window0, window1, write_window) in jobs()}

                        for future in concurrent.futures.as_completed(future_to_window):
                            window0, window1, write_window = future_to_window[future]
                            result = future.result()
                            dst.write(result, 1, window=write_window)
                            bar.update(result.size)

    click.echo((msg.WRITEOUT).format(output))
    click.echo((msg.COMPLETION).format(msg.printtime(t0, time.time())))
