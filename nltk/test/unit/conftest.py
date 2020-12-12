import pytest


@pytest.fixture(autouse=True)
def mock_plot(mocker):
    """ Disable matplotlib plotting in test code """

    try:
        import matplotlib.pyplot as plt

        mocker.patch.object(plt, 'show')
    except ImportError:
        pytest.skip(
            "mock_plot imports matplotlib which doesn't exist!"
        )
