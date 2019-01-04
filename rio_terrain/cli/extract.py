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


def _extract(data, categorical, category):
    if category is None:
        _category = [1]
    else:
        _category = list(category)
    mask = np.isin(categorical, _category)
    result = data*mask
    return result


@click.command()
@click.argument('input', nargs=1, type=click.Path(exists=True))
@click.argument('categorical', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.option('-c', '--category', multiple=True, type=int,
              help='Category to extract.')
@click.option('-j', '--njobs', type=int, default=multiprocessing.cpu_count(),
              help='Number of concurrent jobs to run')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=terrain_version, message='%(version)s')
@click.pass_context
def extract(ctx, input, categorical, output, category, njobs, verbose):
    """Extract areas from a raster by category.

    The categorical raster may be the input raster or another raster.

    \b
    Example:
    rio extract diff.tif categorical.tif extract.tif -c 1 -c 3

    """

    t0 = clock()

    with rasterio.Env():

        with rasterio.open(input) as src, \
                rasterio.open(categorical) as cat:

            profile = src.profile
            affine = src.transform
            step = (affine[0], affine[4])

            if njobs >= 1:
                block_shape = (src.block_shapes)[0]
                blockxsize = block_shape[1]
                blockysize = block_shape[0]
            else:
                blockxsize = None
                blockysize = None

            tiles = rt.tile_grid_intersection(src, cat, blockxsize=blockxsize, blockysize=blockysize)
            windows0, windows1, write_windows, affine, nrows, ncols = tiles

            profile.update(count=1, compress='lzw', bigtiff='yes',
                           height=nrows, width=ncols, transform=affine)

            with rasterio.open(output, 'w', **profile) as dst:
                if njobs < 1:
                    click.echo(msg.INMEMORY)
                    data = src.read(1, window=next(windows0))
                    mask = cat.read(1, window=next(windows1))
                    result = _extract(data, mask, category)
                    dst.write(result, 1, window=next(write_windows))
                elif njobs == 1:
                    click.echo(msg.SEQUENTIAL)
                    for (window0, window1, write_window) in zip(windows0, windows1, write_windows):
                        data = src.read(1, window=window0)
                        mask = cat.read(1, window=window1)
                        result = _extract(data, mask, category)
                        dst.write(result, 1, window=write_window)
                else:
                    click.echo(msg.CONCURRENT)

                    def jobs():
                        for (window0, window1, write_window) in zip(windows0, windows1, write_windows):
                            data = src.read(1, window=window0)
                            mask = cat.read(1, window=window1)
                            yield data, mask, window0, window1, write_window

                    with concurrent.futures.ThreadPoolExecutor(max_workers=njobs) as executor:

                        future_to_window = {
                            executor.submit(
                                _extract,
                                data,
                                mask,
                                category): (window0, window1, write_window)
                            for (data, mask, window0, window1, write_window) in jobs()}

                        for future in concurrent.futures.as_completed(future_to_window):
                            window0, window1, write_window = future_to_window[future]
                            result = future.result()
                            dst.write(result, 1, window=write_window)

    click.echo('Wrote extracted raster to {}'.format(output))

    t1 = clock()
    click.echo('Finished in : {}'.format(msg.printtime(t0, t1)))
