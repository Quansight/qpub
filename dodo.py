"""tasks to reproduce the environment and development environment."""


def task_dev():

    """install dgaf in development mode."""
    return dict(
        actions="""
pip install -rrequirements.txt
python -m dgaf infer develop
    """.strip().splitlines(),
        file_dep=["requirements.txt"],
        uptodate=[False],
    )


def task_setup():

    """install the built dgaf this is used in [github actions] for testing this package on mac, windows, and linux."""

    return dict(
        actions="""
pip install -rrequirements.txt
python -m dgaf infer setup
    """.strip().splitlines(),
        file_dep=["requirements.txt"],
        uptodate=[False],
    )