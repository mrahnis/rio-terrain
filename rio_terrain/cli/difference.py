"""Subtract one single-band raster from another."""

import time
import warnings
import concurrent.futures

import numpy as np
import click
import rasterio

import rio_terrain as rt
import rio_terrain.tools.messages as msg
from rio_terrain import __version__ as plugin_version


@click.command('difference', short_help="Subtract one raster from another.")
@click.argument('input_t0', nargs=1, type=click.Path(exists=True))
@click.argument('input_t1', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.option('-b', '--blocks', 'blocks', nargs=1, type=int, default=40,
              help='Multiple internal blocks to chunk.')
@click.option('-j', '--njobs', type=int, default=1, help='Number of concurrent jobs to run.')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=plugin_version, message='rio-terrain v%(version)s')
@click.pass_context
def difference(ctx, input_t0, input_t1, output, blocks, njobs, verbose):
    """Subtract INPUT_T0 from INPUT_T1.

    \b
    INPUT_T0 should be a single-band raster at time t0.
    INPUT_T1 should be a single-band raster at time t1.

    \b
    Example:
    rio diff elevation1.tif elevation2.tif, diff2_1.tif

    """
    if verbose:
        np.warnings.filterwarnings('default')
    else:
        np.warnings.filterwarnings('ignore')

    t0 = time.time()
    command = click.get_current_context().info_name

    with rasterio.open(input_t0) as src0, rasterio.open(input_t1) as src1:

        if not rt.is_raster_intersecting(src0, src1):
            raise ValueError(msg.NONINTERSECTING)
        # if not rt.is_raster_aligned(src0, src1):
        #    raise ValueError(msg.NONALIGNED)

        profile = src0.profile
        affine = src0.transform

        if njobs >= 1:
            block_shape = (src0.block_shapes)[0]
            blockxsize = block_shape[1]
            blockysize = block_shape[0]
        else:
            blockxsize = None
            blockysize = None

        tiles = rt.tile_grid_intersection(
            src0, src1, blockxsize=blockxsize * blocks, blockysize=blockysize * blocks)
        windows0, windows1, write_windows, affine, nrows, ncols = tiles

        profile.update(
            dtype=rasterio.float32,
            count=1,
            height=nrows,
            width=ncols,
            transform=affine,
            compress='lzw',
            bigtiff='yes',
        )

        with rasterio.open(output, 'w', **profile) as dst:
            if njobs < 1:
                click.echo((msg.STARTING).format(command, msg.INMEMORY))
                img0 = src0.read(1, window=next(windows0))
                img1 = src1.read(1, window=next(windows1))
                img0[img0 <= src0.nodata + 1] = np.nan
                img1[img1 <= src1.nodata + 1] = np.nan
                result = img1 - img0
                dst.write(result.astype(profile['dtype']), 1, window=next(write_windows))
            elif njobs == 1:
                click.echo((msg.STARTING).format(command, msg.SEQUENTIAL))
                with click.progressbar(length=nrows * ncols, label='Blocks done:') as bar:
                    for (window0, window1, write_window) in zip(windows0, windows1, write_windows):
                        img0 = src0.read(1, window=window0)
                        img1 = src1.read(1, window=window1)
                        img0[img0 <= src0.nodata + 1] = np.nan
                        img1[img1 <= src1.nodata + 1] = np.nan
                        result = img1 - img0
                        dst.write(result.astype(profile['dtype']), 1, window=write_window)
                        bar.update(result.size)
            else:
                click.echo((msg.STARTING).format(command, msg.CONCURRENT))

                def jobs():
                    for (window0, window1, write_window) in zip(windows0, windows1, write_windows):
                        img0 = src0.read(1, window=window0)
                        img1 = src1.read(1, window=window1)
                        img0[img0 <= src0.nodata + 1] = np.nan
                        img1[img1 <= src1.nodata + 1] = np.nan
                        yield img0, img1, window0, window1, write_window

                def diff(img0, img1):
                    return img1 - img0

                with concurrent.futures.ThreadPoolExecutor(max_workers=njobs) as executor, \
                        click.progressbar(length=nrows * ncols, label='Blocks done:') as bar:

                    future_to_window = {
                        executor.submit(diff, img0, img1): (
                            window0,
                            window1,
                            write_window,
                        )
                        for (img0, img1, window0, window1, write_window) in jobs()
                    }

                    for future in concurrent.futures.as_completed(future_to_window):
                        window0, window1, write_window = future_to_window[future]
                        result = future.result()
                        dst.write(result.astype(profile['dtype']), 1, window=write_window)
                        bar.update(result.size)

    click.echo((msg.WRITEOUT).format(output))
    click.echo((msg.COMPLETION).format(msg.printtime(t0, time.time())))
