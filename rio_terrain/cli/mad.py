"""Calculate median absolute deviation of a single-band raster"""

import time
import warnings
import concurrent.futures

import click
import numpy as np
import rasterio

import rio_terrain as rt
import rio_terrain.tools.messages as msg
from rio_terrain.core import focalstatistics
from rio_terrain import __version__ as plugin_version


@click.command('mad', short_help="Calculate median abolute deviation.")
@click.argument('input', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.option('-n', '--neighborhood', nargs=1, default=3, help='Neighborhood size in cells.')
@click.option('-b', '--blocks', 'blocks', nargs=1, type=int, default=40,
              help='Multiple internal blocks to chunk.')
@click.option('-j', '--njobs', type=int, default=1, help='Number of concurrent jobs to run.')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=plugin_version, message='rio-terrain v%(version)s')
@click.pass_context
def mad(ctx, input, output, neighborhood, blocks, njobs, verbose):
    """Calculate a median absolute deviation raster.

    INPUT should be a single-band raster.

    \b
    Example:
    rio mad elevation.tif mad.tif

    """
    if verbose:
        warnings.filterwarnings('default')
    else:
        warnings.filterwarnings('ignore')

    t0 = time.time()
    command = click.get_current_context().info_name

    with rasterio.open(input) as src:
        profile = src.profile
        affine = src.transform
        profile.update(
            dtype=rasterio.float32,
            count=1,
            compress='deflate',
            predictor=3,
            bigtiff='yes'
        )

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
                blockshape[0] * blocks,
                blockshape[1] * blocks,
                overlap=neighborhood,
            )
            write_windows = rt.tile_grid(
                src.width,
                src.height,
                blockshape[0] * blocks,
                blockshape[1] * blocks,
                overlap=0,
            )

        with rasterio.open(output, 'w', **profile) as dst:
            if njobs == 0 or njobs == 1:
                if njobs == 0:
                    click.echo((msg.STARTING).format(command, msg.INMEMORY))
                else:
                    click.echo((msg.STARTING).format(command, msg.SEQUENTIAL))
                with click.progressbar(length=src.width * src.height, label='Blocks done:') as bar:
                    for (read_window, write_window) in zip(read_windows, write_windows):
                        img = src.read(1, window=read_window)
                        img[img <= src.nodata + 1] = np.nan
                        arr = focalstatistics.mad(img, size=(neighborhood, neighborhood))
                        result = rt.trim(arr, rt.margins(read_window, write_window))
                        dst.write(result.astype(profile['dtype']), 1, window=write_window)
                        bar.update(result.size)
            else:
                click.echo((msg.STARTING).format(command, msg.CONCURRENT))

                def jobs():
                    for (read_window, write_window) in zip(read_windows, write_windows):
                        img = src.read(1, window=read_window)
                        img[img <= src.nodata + 1] = np.nan
                        yield img, read_window, write_window

                with concurrent.futures.ThreadPoolExecutor(max_workers=njobs) as executor, \
                        click.progressbar(length=src.width*src.height, label='Blocks done:') as bar:

                    future_to_window = {
                        executor.submit(
                            focalstatistics.mad,
                            img,
                            size=(neighborhood, neighborhood),
                        ): (read_window, write_window)
                        for (img, read_window, write_window) in jobs()
                    }

                    for future in concurrent.futures.as_completed(future_to_window):
                        read_window, write_window = future_to_window[future]
                        arr = future.result()
                        result = rt.trim(arr, rt.margins(read_window, write_window))
                        dst.write(result.astype(profile['dtype']), 1, window=write_window)
                        bar.update(result.size)

    click.echo((msg.WRITEOUT).format(output))
    click.echo((msg.COMPLETION).format(msg.printtime(t0, time.time())))
