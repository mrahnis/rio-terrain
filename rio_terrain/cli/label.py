import time
import warnings
import concurrent.futures
import multiprocessing

import click
import numpy as np
import rasterio
import scipy

import rio_terrain as rt
import rio_terrain.tools.messages as msg
from rio_terrain import __version__ as plugin_version


BOX = np.ones((3, 3))
CROSS = np.array([[0, 1, 0],
                  [1, 1, 1],
                  [0, 1, 0]])


@click.command()
@click.argument('input', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.option('--diagonals/--no-diagonals', 'diagonals', default=False,
                help='Label diagonals as connected')
@click.option('--zeros/--no-zeros', is_flag=True,
              help='Use the raster nodata value or zeros for False condition')
@click.option('-j', '--njobs', type=int, default=0,
              help='Number of concurrent jobs to run')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=plugin_version, message='rio-terrain v%(version)s')
@click.pass_context
def label(ctx, input, output, diagonals, zeros, njobs, verbose):
    """Label areas in a raster.

    \b
    Example:
    rio label blobs.tif labeled_blobs.tif

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

            dtype = 'int32'
            nodata = np.iinfo(np.int32).min
            profile.update(dtype=rasterio.int32, nodata=nodata, count=1,
                           compress='lzw')

            if zeros:
                false_val = 0
            else:
                false_val = nodata

            if diagonals is True:
                structure = BOX
            else:
                structure = CROSS

            with rasterio.open(output, 'w', **profile) as dst:
                if njobs < 1:
                    click.echo((msg.STARTING).format('label', msg.INMEMORY))
                    data = src.read(1)
                    labels, count = scipy.ndimage.label(data, structure=structure)
                    labels[data == nodata] = false_val
                    labels[labels == 0] = false_val
                    dst.write(labels.astype(dtype), 1)
                elif njobs == 1:
                    click.echo((msg.STARTING).format('label', msg.SEQUENTIAL))

                    blockshape = (list(src.block_shapes))[0]
                    if (blockshape[0] == 1) or (blockshape[1] == 1):
                        warnings.warn((msg.STRIPED).format(blockshape))
                    read_windows = rt.tile_grid(src.width, src.height, src.width, blockshape[1], overlap=1)
                    write_windows = rt.tile_grid(src.width, src.height, src.width, blockshape[1], overlap=0)

                    overlap = None
                    total = 0
                    for (read_window, write_window) in zip(read_windows, write_windows):
                        data = src.read(1, window=read_window)
                        labels, count = scipy.ndimage.label(data, structure=structure)

                        if overlap is not None:
                            # remap values based on overlap
                            stack = np.stack([np.squeeze(overlap), np.squeeze(data[:1, :])])
                            pairs = np.unique(stack.T, axis=0)
                            idx = np.all(pairs > 0, axis=1)
                            print(pairs[idx])

                            # now remap
                            # can i use numpy.place and extract here?
                            # this strategy won't work in one pass - consider a meander that crosses back and forth over three chunks
                        else:
                            print('overlap empty')
                        total += count
                        # this will need to be the overlap after remapping labels
                        overlap = labels[-1:, :]

                        print(total)
                        # result = labels
                        # dst.write(result.astype(dtype), 1, window=write_window)
                else:
                    click.echo((msg.STARTING).format('label', msg.CONCURRENT))
                    click.echo('NOT IMPLEMENTED')

    click.echo('Wrote {} labels to {}'.format(count, output))
    click.echo((msg.COMPLETION).format(msg.printtime(t0, time.time())))
