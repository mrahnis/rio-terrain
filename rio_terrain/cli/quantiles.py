"""Calculate and print quantile values from a single-band raster."""

import time
import warnings

from itertools import repeat
import concurrent.futures
import multiprocessing
from math import ceil

import click
import numpy as np
import rasterio
from crick import TDigest
from scipy import stats
from scipy.stats.mstats import mquantiles
import matplotlib.pyplot as plt

import rio_terrain as rt
import rio_terrain.tools.messages as msg
from rio_terrain import __version__ as plugin_version


def tdigest_mean(digest):
    """Estimate the mean from a tdigest

    """
    ctr = digest.centroids()
    mean = np.sum(ctr['mean']*ctr['weight'])/np.sum(ctr['weight'])

    return mean


def tdigest_std(digest):
    """Estimate the standard deviation of the mean from a tdigest

    """
    ctr = digest.centroids()
    mean = tdigest_mean(digest)
    std = np.sqrt(
                (np.power((ctr['mean'] - mean), 2)*ctr['weight']).sum()
                / (ctr['weight'].sum() - 1)
                )

    return std


def tdigest_stats(digest):
    """Estimate descriptive statistics from a tdigest

    """
    minX = digest.min()
    maxX = digest.max()
    meanX = tdigest_mean(digest)
    stdX = tdigest_std(digest)

    return (minX, maxX, meanX, stdX)


def digest_window(file, window, absolute):
    '''Process worker that calculates a t-digest on a raster

    '''
    with rasterio.open(file) as src:
        img = src.read(1, window=window[1])
        img[img <= src.nodata+1] = np.nan
        arr = img[np.isfinite(img)]
        if absolute:
            arr = np.absolute(arr)
        count_ = np.count_nonzero(~np.isnan(img))
        digest_ = TDigest()
        digest_.update(arr.flatten())

    return window, digest_, count_


@click.command('quantiles', short_help="Calculate quantile values.")
@click.argument('input', nargs=1, type=click.Path(exists=True))
@click.option('-q', '--quantile', multiple=True, type=float,
              help='Print quantile value.')
@click.option('-f', '--fraction', nargs=1, default=1.0,
              help='Randomly sample a fraction of internal blocks.')
@click.option('--absolute/--no-absolute', default=False,
              help='Calculate quantiles for the absolute values.')
@click.option('--describe/--no-describe', default=False,
              help='Print descriptive statistics to the console.')
@click.option('--plot/--no-plot', default=False,
              help='Display statistics plots.')
@click.option('-j', '--jobs', 'njobs', type=int, default=multiprocessing.cpu_count(),
              help='Number of concurrent jobs to run.')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=plugin_version, message='rio-terrain v%(version)s')
@click.pass_context
def quantiles(ctx, input, quantile, fraction, absolute, describe, plot, njobs, verbose):
    """Calculate and print quantile values.

    INPUT should be a single-band raster.

    \b
    Example:
    rio quantiles elevation.tif -q 0.5 -q 0.9

    """
    if verbose:
        np.warnings.filterwarnings('default')
    else:
        np.warnings.filterwarnings('ignore')

    t0 = time.time()
    command = click.get_current_context().info_name

    count = 0

    with rasterio.open(input) as src:
        profile = src.profile
        affine = src.transform

        if njobs < 1:
            click.echo("Running quantiles in-memory")
            img = src.read(1)
            img[img <= src.nodata+1] = np.nan
            arr = img[np.isfinite(img)]
            if absolute:
                arr = np.absolute(arr)

            count = np.count_nonzero(~np.isnan(img))
            description = (arr.min(), arr.max(), arr.mean(), arr.std())
            results = zip(quantile, mquantiles(arr, np.array(quantile)))

        elif njobs == 1:
            blocks = rt.subsample(src.block_windows(), probability=fraction)
            n_blocks = ceil(rt.block_count(src.shape, src.block_shapes) * fraction)
            digest = TDigest()

            click.echo("Running quantiles with sequential t-digest")
            with click.progressbar(length=n_blocks, label='Blocks done:') as bar:
                for ij, window in blocks:
                    img = src.read(1, window=window)
                    img[img <= src.nodata+1] = np.nan
                    arr = img[np.isfinite(img[:])]
                    if absolute:
                        arr = np.absolute(arr)

                    window_count = np.count_nonzero(~np.isnan(img))
                    if window_count > 0:
                        window_digest = TDigest()
                        window_digest.update(arr.flatten())
                        digest.merge(window_digest)
                        count += window_count
                    bar.update(1)

            description = tdigest_stats(digest)
            results = zip(quantile, digest.quantile(quantile))

        else:

            blocks = rt.subsample(src.block_windows(), probability=fraction)
            n_blocks = ceil(rt.block_count(src.shape, src.block_shapes)*fraction)
            digest = TDigest()

            click.echo("Running quantiles with multiprocess t-digest")
            with concurrent.futures.ProcessPoolExecutor(max_workers=njobs) as executor, \
                    click.progressbar(length=n_blocks, label='Blocks done:') as bar:
                for (window, window_digest, window_count) in executor.map(digest_window, repeat(input), blocks, repeat(absolute)):
                    if window_count > 0:
                        digest.merge(window_digest)
                        count += window_count
                    bar.update(1)

            description = tdigest_stats(digest)
            results = zip(quantile, digest.quantile(quantile))

    click.echo((msg.COMPLETION).format(msg.printtime(t0, time.time())))

    click.echo(list(results))
    minX, maxX, meanX, stdX = description

    if describe:
        click.echo("min: {}".format(minX))
        click.echo("max: {}".format(maxX))
        click.echo("mean: {}".format(meanX))
        click.echo("std: {}".format(stdX))
        click.echo("count: {}".format(count))

    if njobs > 0 and plot is True:

        ctr = digest.centroids()

        # scaled to theoretic normal
        # calculate positions relative to standard normal distribution
        qx_predicted_norm = stats.norm.ppf(digest.cdf(ctr['mean']))
        qx_norm = np.linspace(start=stats.norm.ppf(0.001), stop=stats.norm.ppf(0.999), num=250)
        qz_norm = qx_norm*stdX + meanX
        cum_norm = stats.norm.cdf(qx_norm)

        # scaled to theoretic laplace
        # calculate positions relative to laplace distribution
        """
        qx_predicted_laplace = stats.laplace.ppf(digest.cdf(ctr['mean']))
        qx_laplace = np.linspace(start=stats.laplace.ppf(0.001), stop=stats.laplace.ppf(0.999), num=250)
        qz_laplace = qx_laplace*stdX + mean
        cum_laplace = stats.laplace.cdf(qx_laplace)
        """

        # frequency at centroid (irregular width bins)
        plt.plot(ctr['mean'], ctr['weight'], 'r.')
        plt.plot([meanX], [0], 'k+', markersize=12)
        plt.xlabel('Centroid Value')
        plt.ylabel('Counts')
        plt.title('Centroid Counts')
        plt.show()

        # histogram (equal width bins)
        nbins = 1000
        hist, bin_edges = digest.histogram(nbins)
        width = (digest.max() - digest.min())/nbins
        plt.bar(bin_edges[:-1], hist, width=width)
        plt.xlabel('Value')
        plt.ylabel('Counts')
        plt.title('Histogram')
        plt.show()

        # cumulative probability distribution
        spacing = (digest.max() - digest.min())/100
        samples = np.arange(ctr['mean'].min(), ctr['mean'].max(), spacing)
        cdf = digest.cdf(samples)

        plt.plot(samples, cdf, 'r.')
        plt.plot(qz_norm, cum_norm, linestyle='dashed', c='black')
        # plt.plot(qz_laplace, cum_laplace, linestyle='dotted', c='gray')
        plt.xlabel('Value')
        plt.ylabel('Probability')
        plt.title('Cumulative Distribution')
        plt.plot([meanX], [digest.cdf(meanX)], "k+", markersize=12)
        plt.show()

        # theoretic normal
        plt.plot(qx_predicted_norm, ctr['mean'], 'r.')
        plt.plot(qx_norm, qz_norm, linestyle='dashed', c='black')
        plt.xlabel('Standard Normal Variate')
        plt.ylabel('Value')
        plt.title('QQ-plot on theoretic standard normal')
        plt.plot([0], [meanX], "k+", markersize=12)
        plt.show()

        # theoretic laplace
        """
        plt.plot(qx_predicted_laplace, ctr['mean'], 'r.')
        plt.plot(qx_laplace, qz_laplace, linestyle='dashed', c='black')
        plt.plot([0], [mean], 'k+', markersize=12)
        plt.xlabel('laplace variate')
        plt.ylabel('Elevation (m)')
        plt.title('QQ-plot on theoretic laplace')
        plt.show()
        """
    if njobs < 1 and plot is True:

        # histogram (equal width bins)
        nbins = 100
        hist, bin_edges = np.histogram(arr, nbins)
        width = (arr.max() - arr.min())/nbins
        plt.bar(bin_edges[:-1], hist, width=width)
        plt.xlabel('Elevation (m)')
        plt.ylabel('Counts')
        plt.title('Histogram')
        plt.show()

        # cumulative probability distribution
        cdf = np.cumsum(hist)/count
        qx_predicted_norm = stats.norm.ppf(cdf)

        qx_norm = np.linspace(start=stats.norm.ppf(0.001), stop=stats.norm.ppf(0.999), num=250)
        qz_norm = qx_norm * stdX + meanX
        cum_norm = stats.norm.cdf(qx_norm)

        plt.plot(bin_edges[:-1], cdf, 'r.')
        plt.plot(qz_norm, cum_norm, linestyle='dashed', c='black')
        plt.xlabel('Value')
        plt.ylabel('Probability')
        plt.title('Cumulative Distribution')
        plt.plot([meanX], [0], "k+", markersize=12)
        plt.show()

        # theoretic normal

        # full dataset is too large!
        # zscore = (arr - meanX)/stdX
        # plt.plot(zscore, arr, 'r.')

        plt.plot(qx_predicted_norm, bin_edges[:-1], 'r.')
        plt.plot(qx_norm, qz_norm, linestyle='dashed', c='black')
        plt.xlabel('Standard Normal Variate')
        plt.ylabel('Value')
        plt.title('QQ-plot on theoretic standard normal')
        plt.plot([0], [meanX], "k+", markersize=12)
        plt.show()
