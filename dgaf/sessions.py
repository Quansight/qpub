"""nox sessions that execute command line actions in virtual environments.

this document encodes common practices for command line utilities to package,
document, test, and lint software. nox allows us to control the environments 
each utility operates within.
"""

import nox
from .__init__ import *


@nox.session(python=False)
def develop(session):
    if PYPROJECT_TOML.exists():
        develop_pyproject(session)
    else:
        develop_setuptools(session)


def develop_pyproject(session):
    config = PYPROJECT_TOML.load()
    build_backend = config.get("build-system", {}).get("build-backend", None)
    if build_backend:
        if build_backend == "flit_core.buildapi":
            # install flit, the flit way
            session.install("flit")
            session.run(*"flit install -s".split())
        # if poetry we need to make sure there is setuptools in teh build
        elif build_backend == "setuptools.build_meta":
            develop_setuptools(session)

        elif build_backend == "poetry.core.masonry.api":
            develop_poetry(session)


def develop_setuptools(session):
    """a local install based of off setup.py"""
    session.run(*"pip install -e.".split())


@nox.session(python=False)
def install(session):
    """install the project."""
    # install the conda dependencies
    session.run(*"pip install .".split())


@nox.session(reuse_venv=True)
def build(session):
    if PYPROJECT_TOML.exists():
        build_pep517(session)
    else:
        build_setuptools(session)


def build_pep517(session):
    session.install("pep517")
    session.run(*"python -m pep517.build .".split())


def build_setuptools(session):
    session


@nox.session(python=False)
def lint(session):
    """pre-commit is installed at the top level because it is good at managing environments."""
    session.install(*"pre-commit".split())
    session.run(*"pre-commit run --all-files".split())


@nox.session(reuse_venv=True)
def test(session):
    """pre-commit is installed at the top level because it is good at managing environments."""
    session.run(*"pip install  colorlog . .[test]".split())
    if options.generate_types:
        session.run(*"pip install monkeytype".split())
        session.run(*"monkeytype run -m pytest".split())
    else:
        session.run(*"pytest".split())


@nox.session(reuse_venv=True)
def docs(session):
    session.install(
        *"jupyter-book>=0.9 doit GitPython depfinder aiofiles appdirs typer nox pathspec requests-cache tomlkit".split()
    )
    if options.watch:
        session.run(*f"python -m dgaf.tasks auto --dir . -s html".split())
    else:
        session.run(*f"python -m dgaf.tasks html".split())

    if options.serve:
        session.run(*f"python -m http.server -d docs/_build/html".split())


@nox.session(reuse_venv=True)
def blog(session):
    session


@nox.session(reuse_venv=True)
def configure(session):
    """produce the configuration for different distributions."""
    session.install(
        *"doit GitPython depfinder aiofiles appdirs typer nox json-e pathspec requests-cache tomlkit".split()
    )
    session.run(
        *f"""python -m dgaf.tasks lint docs python gitignore""".split(),
        env=options.dump(),
    )


@nox.session(reuse_venv=True)
def doit(session, module: str = None, file: Path = None):
    """produce the configuration for different distributions."""
    session.install(*"doit".split())
    session.install(*project.get_requires())
    file = project.fs.get_module_name()[1]
    session.run(
        *f"""python -m doit --dir . --file {file} """.split() + session.posargs,
        env=options.dump(),
    )
