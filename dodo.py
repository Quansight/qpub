"""tasks to reproduce the environment and development environment."""


def configure():
    """we call the functions directly to avoid write conflicts"""
    import dgaf.tasks

    dgaf.tasks.make_pyproject()
    dgaf.tasks.add_dependencies()
    dgaf.tasks.make_python_setup()


def dev():
    """we call the functions directly to avoid write conflicts"""
    import dgaf.tasks

    dgaf.tasks.develop()


def task_dev():

    """install dgaf in development mode."""

    return dict(
        actions=[dev],
        task_dep=["setup"],
        uptodate=[False],
    )


def task_setup():

    """install the built dgaf this is used in [github actions] for testing this package on mac, windows, and linux."""

    return dict(
        actions=["""pip install -rrequirements.txt""", configure],
        file_dep=["requirements.txt"],
        targets=["poetry.lock"],
    )
