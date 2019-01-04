from time import clock
import warnings
import concurrent.futures
import multiprocessing

import numpy as np
import click
import rasterio

import rio_terrain as rt
import rio_terrain.tools.messages as msg
from rio_terrain import __version__ as terrain_version


@click.command()
@click.argument('input_t0', nargs=1, type=click.Path(exists=True))
@click.argument('input_t1', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.option('-j', '--njobs', type=int, default=multiprocessing.cpu_count(),
              help='Number of concurrent jobs to run.')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=terrain_version, message='%(version)s')
@click.pass_context
def difference(ctx, input_t0, input_t1, output, njobs, verbose):
    """Subtracts one raster from another.

    \b
    Example:
    rio diff elevation1.tif elevation2.tif, diff2_1.tif

    """

    t0 = clock()

    with rasterio.Env():

        with rasterio.open(input_t0) as src0, rasterio.open(input_t1) as src1:
            profile = src0.profile
            affine = src0.transform
            step = (affine[0], affine[4])

            if njobs >= 1:
                block_shape = (src0.block_shapes)[0]
                blockxsize = block_shape[1]
                blockysize = block_shape[0]
            else:
                blockxsize = None
                blockysize = None

            tiles = rt.tile_grid_intersection(src0, src1, blockxsize=blockxsize, blockysize=blockysize)
            windows0, windows1, write_windows, affine, nrows, ncols = tiles

            profile.update(dtype=rasterio.float32, count=1,
                           height=nrows, width=ncols, transform=affine,
                           compress='lzw', bigtiff='yes')

            with rasterio.open(output, 'w', **profile) as dst:
                if njobs < 1:
                    click.echo(msg.INMEMORY)
                    data0 = src0.read(1, window=next(windows0))
                    data1 = src1.read(1, window=next(windows1))
                    data0[data0 <= src0.nodata+1] = np.nan
                    data1[data1 <= src1.nodata+1] = np.nan
                    result = data1 - data0
                    dst.write(result, 1, window=next(write_windows))
                elif njobs == 1:
                    click.echo(msg.SEQUENTIAL)
                    for (window0, window1, write_window) in zip(windows0, windows1, write_windows):
                        data0 = src0.read(1, window=window0)
                        data1 = src1.read(1, window=window1)
                        data0[data0 <= src0.nodata+1] = np.nan
                        data1[data1 <= src1.nodata+1] = np.nan
                        result = data1 - data0
                        dst.write(result, 1, window=write_window)
                else:
                    click.echo(msg.CONCURRENT)

                    def jobs():
                        for (window0, window1, write_window) in zip(windows0, windows1, write_windows):
                            data0 = src0.read(1, window=window0)
                            data1 = src1.read(1, window=window1)
                            data0[data0 <= src0.nodata+1] = np.nan
                            data1[data1 <= src1.nodata+1] = np.nan
                            yield data0, data1, window0, window1, write_window

                    def diff(data0, data1):
                        return data1 - data0

                    with concurrent.futures.ThreadPoolExecutor(max_workers=njobs) as executor:

                        future_to_window = {
                            executor.submit(
                                diff,
                                data0,
                                data1): (window0, window1, write_window)
                            for (data0, data1, window0, window1, write_window) in jobs()}

                        for future in concurrent.futures.as_completed(future_to_window):
                            window0, window1, write_window = future_to_window[future]
                            result = future.result()
                            dst.write(result, 1, window=write_window)

    click.echo('Wrote difference raster to {}'.format(output))

    t1 = clock()
    click.echo('Finished in : {}'.format(msg.printtime(t0, t1)))
