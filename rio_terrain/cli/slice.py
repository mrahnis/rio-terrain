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


def _slice(data, minimum=None, maximum=None, keep_data=False, false_val=0):
    """Slice data or ones from an array given a value range.

    Parameters:
        data (ndarray)
        minimum (float)
        maximum (float)
        keep_data (bool)

    Returns:
        result (ndarray)

    """

    # default bounds
    if minimum is None:
        minimum = np.nanmin(data)
    if maximum is None:
        maximum = np.nanmax(data)

    if keep_data:
        result = np.where((data >= minimum) & (data <= maximum), data, false_val)
    else:
        result = np.where((data >= minimum) & (data <= maximum), 1, false_val)

    return result


@click.command()
@click.argument('input', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.option('--minimum', nargs=1, type=float, default=None,
              help='Minimum value to extract.')
@click.option('--maximum', nargs=1, type=float, default=None,
              help='Maximum value to extract.')
@click.option('--keep-data/--no-keep-data', is_flag=True,
              help='Return the input data. Default is to return ones.')
@click.option('--zeros/--no-zeros', is_flag=True,
              help='Use the raster nodata value or zeros for False condition')
@click.option('-j', '--njobs', type=int, default=multiprocessing.cpu_count(),
              help='Number of concurrent jobs to run')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=plugin_version, message='rio-terrain v%(version)s')
@click.pass_context
def slice(ctx, input, output, minimum, maximum, keep_data, zeros, njobs, verbose):
    """Extract areas from a raster by a data range.

    Setting the --keep-data option will return the data values.
    The default is to return a raster of ones and zeros.

    \b
    Example:
    rio range diff.tif extracted.tif --minumum -2.0 --maximum 2.0

    """
    if verbose:
        np.warnings.filterwarnings('default')
    else:
        np.warnings.filterwarnings('ignore')

    t0 = time.time()

    with rasterio.Env():

        with rasterio.open(input) as src:

            profile = src.profile
            affine = src.transform
            step = (affine[0], affine[4])

            if keep_data:
                dtype = profile['dtype']
                nodata = profile['nodata']
                profile.update(count=1, compress='lzw')
            else:
                dtype = 'int32'
                nodata = np.iinfo(np.int32).min
                profile.update(dtype=rasterio.int32, nodata=nodata, count=1,
                               compress='lzw')

            if zeros:
                false_val = 0
            else:
                false_val = nodata

            with rasterio.open(output, 'w', **profile) as dst:
                if njobs < 1:
                    click.echo((msg.STARTING).format('slice', msg.INMEMORY))
                    data = src.read(1)
                    result = _slice(data, minimum, maximum, keep_data, false_val)
                    dst.write(result.astype(dtype), 1)
                elif njobs == 1:
                    click.echo((msg.STARTING).format('slice', msg.SEQUENTIAL))
                    with click.progressbar(length=src.width*src.height, label='Blocks done:') as bar:
                        for (ij, window) in src.block_windows():
                            data = src.read(1, window=window)
                            result = _slice(data, minimum, maximum, keep_data, false_val)
                            dst.write(result.astype(dtype), 1, window=window)
                            bar.update(result.size)
                else:
                    click.echo((msg.STARTING).format('slice', msg.CONCURRENT))

                    def jobs():
                        for (ij, window) in src.block_windows():
                            data = src.read(1, window=window)
                            yield data, window

                    with concurrent.futures.ThreadPoolExecutor(max_workers=njobs) as executor, \
                            click.progressbar(length=src.width*src.height, label='Blocks done:') as bar:

                        future_to_window = {
                            executor.submit(
                                _slice,
                                data,
                                minimum,
                                maximum,
                                keep_data,
                                false_val): (window)
                            for (data, window) in jobs()}

                        for future in concurrent.futures.as_completed(future_to_window):
                            window = future_to_window[future]
                            result = future.result()
                            dst.write(result.astype(dtype), 1, window=window)
                            bar.update(result.size)

    click.echo((msg.WRITEOUT).format(output))
    click.echo((msg.COMPLETION).format(msg.printtime(t0, time.time())))
