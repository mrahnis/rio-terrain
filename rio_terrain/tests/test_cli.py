from pkg_resources import iter_entry_points

from click.testing import CliRunner

import rasterio
from rasterio.rio.main import main_group

import rio_terrain


def test_version():
    runner = CliRunner()
    result = runner.invoke(main_group, ['aspect', '--version'])
    assert result.exit_code == 0
    assert rio_terrain.__version__ in result.output


def test_all_registered():
    # This test makes sure that all of the subcommands defined in the
    # rasterio.rio_commands entry-point are actually registered to the main
    # cli group.
    for ep in iter_entry_points('rasterio.rio_commands'):
        assert ep.name in main_group.commands


def test_aspect():
    runner = CliRunner()
    result = runner.invoke(main_group, ['aspect', '--help'])
    assert result.exit_code == 0


def test_curvature():
    runner = CliRunner()
    result = runner.invoke(main_group, ['curvature', '--help'])
    assert result.exit_code == 0


def test_difference():
    runner = CliRunner()
    result = runner.invoke(main_group, ['difference', '--help'])
    assert result.exit_code == 0


def test_extract():
    runner = CliRunner()
    result = runner.invoke(main_group, ['extract', '--help'])
    assert result.exit_code == 0


def test_mad():
    runner = CliRunner()
    result = runner.invoke(main_group, ['mad', '--help'])
    assert result.exit_code == 0


def test_quantiles():
    runner = CliRunner()
    result = runner.invoke(main_group, ['quantiles', '--help'])
    assert result.exit_code == 0


def test_slice():
    runner = CliRunner()
    result = runner.invoke(main_group, ['slice', '--help'])
    assert result.exit_code == 0


def test_slope():
    runner = CliRunner()
    result = runner.invoke(main_group, ['slope', '--help'])
    assert result.exit_code == 0


def test_std():
    runner = CliRunner()
    result = runner.invoke(main_group, ['std', '--help'])
    assert result.exit_code == 0


def test_threshold():
    runner = CliRunner()
    result = runner.invoke(main_group, ['threshold', '--help'])
    assert result.exit_code == 0


def test_uncertainty():
    runner = CliRunner()
    result = runner.invoke(main_group, ['uncertainty', '--help'])
    assert result.exit_code == 0
