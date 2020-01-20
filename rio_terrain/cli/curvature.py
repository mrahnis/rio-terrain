"""Calculate curvature of a single-band raster."""

import time
import warnings

import concurrent.futures

import click
import numpy as np
import rasterio

import rio_terrain as rt
import rio_terrain.tools.messages as msg
from rio_terrain import __version__ as plugin_version


@click.command('curvature', short_help="Calculate curvature.")
@click.argument('input', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.option('--neighbors', type=click.Choice(['4', '8']), default='4',
              help='Specifies the number of neighboring cells to use.')
@click.option('--stats/--no-stats', is_flag=True, default=False,
              help='Print basic curvature statistics.')
@click.option('-j', '--njobs', type=int, default=1, help='Number of concurrent jobs to run.')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=plugin_version, message='rio-terrain v%(version)s')
@click.pass_context
def curvature(ctx, input, output, neighbors, stats, njobs, verbose):
    """Calculate curvature of a raster.

    INPUT should be a single-band raster.

    \b
    Example:
    rio curvature elevation.tif curvature.tif

    """
    if verbose:
        np.warnings.filterwarnings('default')
    else:
        np.warnings.filterwarnings('ignore')
        # np.seterr(divide='ignore', invalid='ignore')

    t0 = time.time()
    command = click.get_current_context().info_name

    with rasterio.open(input) as src:
        profile = src.profile
        affine = src.transform
        res = (affine[0], affine[4])
        profile.update(dtype=rasterio.float32, count=1, compress='lzw')

        if (njobs >= 1) and src.is_tiled:
            blockshape = (list(src.block_shapes))[0]
            if (blockshape[0] == 1) or (blockshape[1] == 1):
                warnings.warn((msg.STRIPED).format(blockshape))
            read_windows = rt.tile_grid(
                src.width, src.height, blockshape[0], blockshape[1], overlap=2)
            write_windows = rt.tile_grid(
                src.width, src.height, blockshape[0], blockshape[1], overlap=0)
        else:
            warnings.warn((msg.NOTILING).format(blockshape))

        with rasterio.open(output, 'w', **profile) as dst:
            if njobs < 1:
                click.echo((msg.STARTING).format(command, msg.INMEMORY))
                img = src.read(1)
                img[img <= src.nodata + 1] = np.nan
                result = rt.curvature(img, res=res, neighbors=int(neighbors))
                dst.write(result.astype(profile['dtype']), 1)
            elif njobs == 1:
                click.echo((msg.STARTING).format(command, msg.SEQUENTIAL))
                with click.progressbar(length=src.width * src.height, label='Blocks done:') as bar:
                    for (read_window, write_window) in zip(read_windows, write_windows):
                        img = src.read(1, window=read_window)
                        img[img <= src.nodata + 1] = np.nan
                        arr = rt.curvature(img, res=res, neighbors=int(neighbors))
                        result = rt.trim(arr, rt.margins(read_window, write_window))
                        dst.write(result.astype(profile['dtype']), 1, window=write_window)
                        bar.update(result.size)
            else:
                def jobs():
                    for (read_window, write_window) in zip(read_windows, write_windows):
                        img = src.read(1, window=read_window)
                        img[img <= src.nodata + 1] = np.nan
                        yield img, read_window, write_window

                click.echo((msg.STARTING).format(command, msg.CONCURRENT))
                with concurrent.futures.ThreadPoolExecutor(max_workers=njobs) as executor, \
                        click.progressbar(length=src.width * src.height, label='Blocks done:') as bar:

                    future_to_window = {
                        executor.submit(
                            rt.curvature, img, res=res, neighbors=int(neighbors)
                        ): (read_window, write_window)
                        for img, read_window, write_window in jobs()
                    }

                    for future in concurrent.futures.as_completed(future_to_window):
                        read_window, write_window = future_to_window[future]
                        arr = future.result()
                        result = rt.trim(arr, rt.margins(read_window, write_window))
                        dst.write(result.astype(profile['dtype']), 1, window=write_window)
                        bar.update(result.size)

    click.echo((msg.WRITEOUT).format(output))
    click.echo((msg.COMPLETION).format(msg.printtime(t0, time.time())))
