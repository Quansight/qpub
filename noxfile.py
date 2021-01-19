#!/usr/bin/env -vS nox -f

"""qpub uses nox to bootstrap itself.

the top-level nox file bootstraps qpub for development and ci.
"""
import pathlib

DOIT_CONFIG = dict(verbosity=2)


def task_python_gitignore():
    """download the gitignore file for excluding python content."""

    qpub = pathlib.Path("qpub")
    targets = [
        qpub / "templates" / "Python.gitignore",
        qpub / "templates" / "Nikola.gitignore",
        qpub / "templates" / "JupyterNotebooks.gitignore",
    ]

    return dict(
        actions=[
            """wget https://raw.githubusercontent.com/github/gitignore/master/Python.gitignore -O qpub/templates/Python.gitignore""",
            """wget https://raw.githubusercontent.com/github/gitignore/master/community/Python/Nikola.gitignore -O qpub/templates/Nikola.gitignore""",
            """wget https://raw.githubusercontent.com/github/gitignore/master/community/Python/ .gitignore -O qpub/templates/JupyterNotebooks.gitignore""",
        ],
        targets=targets,
        uptodate=list(map(pathlib.Path.exists, targets)),
    )


def task_readme():
    def template():
        import doit

        action = doit.tools.CmdAction("qpub")
        action.execute()
        pathlib.Path("README.md").write_text(
            pathlib.Path("_README_TEMPLATE.md").read_text().format(commands=action.out)
        )

    return dict(actions=[template])


try:
    import nox
except ModuleNotFoundError:
    raise SystemExit(0)

nox.options.sessions = ["develop"]


@nox.session(python=False)
def quick(session):
    """a quick test session to see if things work."""
    session.install(".")
    session.run(*"qpub test".split())


@nox.session(python=False)
def develop(session):
    """setup to project for development.

    it installs flit, nox, and typer as dependencies.
    """
    session.install("flit")
    session.run(*"flit install -s --deps production".split())


@nox.session(python=False)
def test(session):
    """test the project using qpub

    extra arguments after `--` are passed to pytest.
    the pytest configuration is set in pyproject.toml file.
    """
    # session.run(*"python -m qpub a  dd lint --qpub . lint".split())
    # session.run(*"python -m qpub lint".split())
    session.run(*"python -m qpub test".split(), *session.posargs)


@nox.session(python=False)
def install(session):
    """install the project for real."""
    session.run(*"pip install .".split())


@nox.session(python=False)
def uninstall(session):
    """uninstall the project"""
    session.run(*"pip uninstall -y qpub".split())


@nox.session(python=False)
def docs(session):
    """build the docs with qpub."""
    session.run(*"python -m qpub docs --qpub .".split(), *session.posargs)


@nox.session(reuse_venv=True)
def uml(session):
    """export a visual representation of the project."""
    session.install("pylint")
    session.run(*"pyreverse -o png src.qpub".split())


@nox.session(reuse_venv=True)
def tasks(session):
    session.install("doit")
    session.run(*f"doit -v2 --file={__file__} python_gitignore ".split())
