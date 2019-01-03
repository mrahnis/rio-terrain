from __future__ import print_function

from time import clock
import warnings

import concurrent.futures
import multiprocessing

import click
import numpy as np
import rasterio

import rio_terrain as rt
import rio_terrain.tools.messages as msg
from rio_terrain import __version__ as terrain_version


@click.command()
@click.argument('input', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.option('--neighbors', type=click.Choice(['4', '8']), default='4',
              help='Specifies the number of neighboring cells to use.')
@click.option('-u', '--units', type=click.Choice(['grade','degrees']), default='grade',
              help='Specifies the units of slope.')
@click.option('-j', '--njobs', type=int, default=multiprocessing.cpu_count(),
              help='Number of concurrent jobs to run.')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=terrain_version, message='%(version)s')
@click.pass_context
def slope(ctx, input, output, neighbors, units, njobs, verbose):
    """Calculates slope of a height raster.

    \b
    Example:
    rio slope elevation.tif slope.tif

    """

    t0 = clock()

    with rasterio.Env():

        with rasterio.open(input) as src:
            profile = src.profile
            affine = src.transform
            step = (affine[0], affine[4])
            profile.update(dtype=rasterio.float32, count=1, compress='lzw')

            if njobs >= 1:
                blockshape = (list(src.block_shapes))[0]
                if (blockshape[0] == 1) or (blockshape[1] == 1):
                    warnings.warn((msg.STRIPED).format(blockshape))
                read_windows = rt.tile_grid(src.width, src.height, blockshape[0], blockshape[1], overlap=2)
                write_windows = rt.tile_grid(src.width, src.height, blockshape[0], blockshape[1], overlap=0)

            with rasterio.open(output, 'w', **profile) as dst:

                if njobs < 1:
                    click.echo(msg.INMEMORY)

                    data = src.read(1)
                    data[data <= src.nodata+1] = np.nan
                    result = rt.slope(data, step=step, units=units, neighbors=int(neighbors))
                    dst.write(result, 1)
                elif njobs == 1:
                    click.echo(msg.SEQUENTIAL)

                    # for (_, read_window, write_window, olap) in rt.tiled_windows(src.height, src.width, block_width=128, block_height=128, overlap=2):
                    for (read_window, write_window) in zip(read_windows, write_windows):
                        data = src.read(1, window=read_window)
                        data[data <= src.nodata+1] = np.nan
                        arr = rt.slope(data, step=step, units=units, neighbors=int(neighbors))
                        result = rt.trim(arr, rt.margins(read_window, write_window))
                        dst.write(result, 1, window=write_window)
                else:
                    click.echo(msg.CONCURRENT)

                    def jobs():
                        for (read_window, write_window) in zip(read_windows, write_windows):
                            data = src.read(1, window=read_window)
                            data[data <= src.nodata+1] = np.nan
                            yield data, read_window, write_window

                    with concurrent.futures.ThreadPoolExecutor(max_workers=njobs) as executor:

                        future_to_window = {
                            executor.submit(
                                rt.slope,
                                data,
                                step=step,
                                units=units,
                                neighbors=int(neighbors)): (read_window, write_window)
                            for (data, read_window, write_window) in jobs()}

                        for future in concurrent.futures.as_completed(future_to_window):
                            read_window, write_window = future_to_window[future]
                            arr = future.result()
                            result = rt.trim(arr, rt.margins(read_window, write_window))
                            dst.write(result, 1, window=write_window)

    t1 = clock()
    click.echo('Finished in : {}'.format(msg.printtime(t0, t1)))
