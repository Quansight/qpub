"""tasks to reproduce the environment and development environment."""


def task_dev():
    return dict(
        actions=["pip install -e . --ignore-installed"],
        task_dep=["setup"],
        uptodate=[False],
    )


def task_setup():

    """install the built dgaf this is used in [github actions] for testing this package on mac, windows, and linux."""
    import os

    def configure():
        """we call the functions directly to avoid write conflicts"""

        import dgaf

        distribution = dgaf.base.Distribution()
        distribution.to_setup_cfg()
        distribution.to_setup_py()

    actions = ["""pip install -rrequirements.txt""", configure]
    if os.getenv("CI"):
        actions = [
            """python -m pip install --upgrade pip wheel doit setuptools"""
        ] + actions

    return dict(
        actions=actions,
        file_dep=["requirements.txt"],
        # targets=["poetry.lock"],
    )
