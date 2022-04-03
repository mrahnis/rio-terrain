import pytest

from click.testing import CliRunner


"""pytest fixtures"""


@pytest.fixture(scope='function')
def runner():
    return CliRunner()
