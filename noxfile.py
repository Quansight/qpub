#!/usr/bin/env -vS nox -f

"""dgaf uses nox to bootstrap itself.

the top-level nox file bootstraps dgaf for development and ci.
"""


def task_python_gitignore():
    """download the gitignore file for excluding python content."""
    import pathlib

    dgaf = pathlib.Path("dgaf")
    targets = [
        dgaf / "templates" / "Python.gitignore",
        dgaf / "templates" / "Nikola.gitignore",
        dgaf / "templates" / "JupyterNotebooks.gitignore",
    ]

    return dict(
        actions=[
            """wget https://raw.githubusercontent.com/github/gitignore/master/Python.gitignore -O dgaf/templates/Python.gitignore""",
            """wget https://raw.githubusercontent.com/github/gitignore/master/community/Python/Nikola.gitignore -O dgaf/templates/Nikola.gitignore""",
            """wget https://raw.githubusercontent.com/github/gitignore/master/community/Python/ .gitignore -O dgaf/templates/JupyterNotebooks.gitignore""",
        ],
        targets=targets,
        uptodate=list(map(pathlib.Path.exists, targets)),
    )


try:
    import nox
except ModuleNotFoundError:
    raise SystemExit(0)

nox.options.sessions = ["develop"]


@nox.session(python=False)
def quick(session):
    session.install(".")
    session.run(*"dgaf test".split())


@nox.session(python=False)
def develop(session):
    """setup to project for development.

    it installs flit, nox, and typer as dependencies.
    """
    session.install("flit")
    session.run(*"flit install -s --deps production".split())


@nox.session(python=False)
def test(session):
    """test the project using dgaf

    extra arguments after `--` are passed to pytest.
    the pytest configuration is set in pyproject.toml file.
    """
    # session.run(*"python -m dgaf a  dd lint --dgaf . lint".split())
    # session.run(*"python -m dgaf lint".split())
    session.run(*"python -m dgaf test".split(), *session.posargs)


@nox.session(python=False)
def install(session):
    """install the project for real."""
    session.run(*"pip install .".split())


@nox.session(python=False)
def uninstall(session):
    """uninstall the project"""
    session.run(*"pip uninstall -y dgaf".split())


@nox.session(python=False)
def docs(session):
    """build the docs with dgaf."""
    session.run(*"python -m dgaf docs --dgaf .".split(), *session.posargs)


@nox.session(reuse_venv=True)
def uml(session):
    """export a visual representation of the project."""
    session.install("pylint")
    session.run(*"pyreverse -o png src.dgaf".split())


@nox.session(reuse_venv=True)
def tasks(session):
    session.install("doit")
    session.run(*f"doit -v2 --file={__file__} python_gitignore ".split())
