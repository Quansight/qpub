"""tasks to reproduce the environment and development environment."""


def task_dev():
    return dict(
        actions=["pip install -e . --ignore-installed"],
        task_dep=["setup"],
        uptodate=[False],
    )


def bootstrap():
    distribution = __import__("dgaf").base.Distribution()
    distribution.to_setup_cfg()
    distribution.to_setup_py()


def task_setup():

    """install the built dgaf this is used in [github actions] for testing this package on mac, windows, and linux."""
    import os, inspect

    actions = [
        """pip install -rrequirements.txt""",
        f"""python -c '{"".join(map(str.lstrip, inspect.getsourcelines(bootstrap)[0][1:]))}'""",
    ]
    if os.getenv("CI"):
        actions = ["""python -m pip install --upgrade pip wheel setuptools"""] + actions

    return dict(
        actions=actions,
        file_dep=["requirements.txt"],
        targets=["setup.cfg", "setup.py"],
    )
