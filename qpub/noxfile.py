import shutil
from pathlib import Path

import doit
import git
import nox
from . import util

# this file can share objects with main when the cli is running.
# only parts of the configuration are passed through the environment to doit.
extra = (
    "depfinder appdirs requests-cache aiofiles".split()
    + "tomlkit configupdater ruamel.yaml".split()
)


@nox.session(reuse_venv=True)
def lint(session):
    """format and lint the project."""

    # linting inspects the suffixes in the repository with Git
    # doit orchestrates tasks.
    session.install(*"pre-commit GitPython doit".split())

    # configure the linting configuration.
    # change the directory.
    session.run(*f"""doit --dir . -f {Path(__file__).parent/"lint.py"}""".split())

    # use pre-commit to orchestrate.
    session.run(*"pre-commit run --all-files".split())


@nox.session(reuse_venv=True)
def docs(session):
    """build the documentation with jupyter book, sphinx, or mkdocs."""
    session.install(*"jupyter-book GitPython doit".split())
    session.run(*f"""doit --dir . -f {Path(__file__).parent/"docs_.py"}""".split())
    session.run(
        *"jupyter-book build .  --path-output docs --toc docs/_toc.yml --config docs/_config.yml".split()
    )


@nox.session(reuse_venv=True)
def poetry(session):
    """configure the project to install with poetry."""
    session.install(*"poetry doit GitPython".split() + extra)
    session.run(
        *f"""doit --dir . -v100 -f {Path(__file__).parent/"poetry_.py"}""".split()
    )
    # i dont think development mode works for poetry.
    session.run(*"pip install -e .".split(), external=True)


@nox.session(reuse_venv=True)
def flit(session):
    """configure the project to install with flit."""
    import contextlib, io

    session.install(*"doit GitPython".split() + extra)
    session.run(
        *f"""doit --dir . -v100 -f {Path(__file__).parent/"flit_.py"}""".split()
    )
    session.run(*"pip install flit".split(), external=True)
    session.run(*"flit install -s".split(), external=True)


@nox.session(reuse_venv=True)
def setuptools(session):
    """configure the project to install with setuptools"""
    session.install(*"setuptools wheel doit GitPython".split() + extra)
    session.run(
        *f"""doit --dir . -v100 -f {Path(__file__).parent/"setuptools_.py"}""".split()
    )
    session.run(*"pip install -e .".split(), external=True)


@nox.session(reuse_venv=True)
def local(session):
    """do make a module just requirements or environments."""
    session.install(*"setuptools wheel doit GitPython".split() + extra)
    session.run(
        *f"""doit --dir . -v100 -f {Path(__file__).parent/"local_.py"}""".split()
    )


@nox.session(reuse_venv=True)
def test(session):
    """test the project."""
    session.install("pathspec")
    session.run(
        *f"""doit --dir . -v100 -f {Path(__file__).parent/"test_.py"}""".split()
    )

    session.run("pytest")


@nox.session(python=False)
def develop(session):
    """install the project"""
    # read the build system to figure out how to develop things.
    session.run(*"pip install -e.".split())


@nox.session(python=False)
def build(session):
    """build the project"""
    # flit poetry setuptools
    session.run(*"pip install -e.".split())


@nox.session(python=False)
def install(session):
    """install the project"""
    session.run(*"pip install .".split())


@nox.session(reuse_venv=True)
def help(session):
    """"""
    session.install("ranger-fm")
