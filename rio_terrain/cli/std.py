import time
import warnings
import concurrent.futures
import multiprocessing
from math import ceil

import click
import numpy as np
import rasterio

import rio_terrain as rt
import rio_terrain.tools.messages as msg
from rio_terrain.core import focalstatistics
from rio_terrain import __version__ as plugin_version


@click.command()
@click.argument('input', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.option('-n', '--neighborhood', nargs=1, default=3,
              help='Neigborhood size in cells')
@click.option('-b', '--blocks', 'blocks', nargs=1, type=int, default=40,
              help='Multiply TIFF block size by an amount to make chunks')
@click.option('-j', '--njobs', type=int, default=multiprocessing.cpu_count(),
              help='Number of concurrent jobs to run')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=plugin_version, message='rio-terrain v%(version)s')
@click.pass_context
def std(ctx, input, output, neighborhood, blocks, njobs, verbose):
    """Calculates a standard deviation raster.

    \b
    Example:
    rio std elevation.tif stddev.tif

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
            profile.update(dtype=rasterio.float32, count=1, compress='lzw', bigtiff='yes')

            if njobs >= 1:
                blockshape = (list(src.block_shapes))[0]
                if (blockshape[0] == 1) or (blockshape[1] == 1):
                    warnings.warn((msg.STRIPED).format(blockshape))
                read_windows = rt.tile_grid(src.width, src.height, blockshape[0]*blocks, blockshape[1]*blocks, overlap=neighborhood)
                write_windows = rt.tile_grid(src.width, src.height, blockshape[0]*blocks, blockshape[1]*blocks, overlap=0)

            with rasterio.open(output, 'w', **profile) as dst:
                if njobs < 1:
                    click.echo((msg.STARTING).format('std', msg.INMEMORY))
                    data = src.read(1)
                    data[data <= src.nodata+1] = np.nan
                    result = focalstatistics.std(data, size=(neighborhood, neighborhood))
                    dst.write(result, 1)
                elif njobs == 1:
                    click.echo((msg.STARTING).format('std', msg.SEQUENTIAL))
                    with click.progressbar(length=src.width*src.height, label='Blocks done:') as bar:
                        for (read_window, write_window) in zip(read_windows, write_windows):
                            data = src.read(1, window=read_window)
                            data[data <= src.nodata+1] = np.nan
                            arr = focalstatistics.std(data, size=(neighborhood, neighborhood))
                            result = rt.trim(arr, rt.margins(read_window, write_window))
                            dst.write(result, 1, window=write_window)
                            bar.update(result.size)
                else:
                    click.echo((msg.STARTING).format('std', msg.CONCURRENT))
                    import dask.array as da

                    with click.progressbar(length=src.width*src.height, label='Blocks done:') as bar:
                        for (read_window, write_window) in zip(read_windows, write_windows):
                            data = src.read(1, window=read_window)
                            data[data <= src.nodata+1] = np.nan

                            chunks_wanted = 100
                            bw = ceil(read_window.width/np.sqrt(chunks_wanted)/blockshape[0])
                            bh = ceil(read_window.height/np.sqrt(chunks_wanted)/blockshape[1])
                            hh, ww = rt.chunk_dims((data.shape[0], data.shape[1]), (blockshape[0]*bw, blockshape[1]*bh), min_size=blockshape[0]*2)

                            arr = da.from_array(data, chunks=(tuple(hh), tuple(ww)))
                            tiles_in = da.overlap.overlap(arr, depth={0: neighborhood, 1: neighborhood},
                                                          boundary={0: np.nan, 1: np.nan})
                            tiles_out = tiles_in.map_blocks(focalstatistics.std,
                                                            size=(neighborhood, neighborhood),
                                                            dtype=np.float64)
                            trim_out = da.overlap.trim_internal(tiles_out, {0: neighborhood, 1: neighborhood})
                            full_result = trim_out.compute()
                            result = rt.trim(full_result, rt.margins(read_window, write_window))

                            dst.write(result.astype(profile['dtype']), 1, window=write_window)
                            bar.update(result.size)

                    """
                    def jobs():
                        for (read_window, write_window) in zip(read_windows, write_windows):
                            data = src.read(1, window=read_window)
                            data[data <= src.nodata+1] = np.nan
                            yield data, read_window, write_window

                    with concurrent.futures.ThreadPoolExecutor(max_workers=njobs) as executor, \
                            click.progressbar(length=src.width*src.height, label='Blocks done:') as bar:

                        future_to_window = {
                            executor.submit(
                                focalstatistics.std,
                                data,
                                size=(neighborhood, neighborhood)): (read_window, write_window)
                            for (data, read_window, write_window) in jobs()}

                        for future in concurrent.futures.as_completed(future_to_window):
                            read_window, write_window = future_to_window[future]
                            arr = future.result()
                            result = rt.trim(arr, rt.margins(read_window, write_window))
                            dst.write(result, 1, window=write_window)
                            bar.update(result.size)
                    """

    click.echo((msg.WRITEOUT).format(output))
    click.echo((msg.COMPLETION).format(msg.printtime(t0, time.time())))
