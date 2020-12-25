"""the cli & nox session for the qpub application"""

import typer
import nox
import pathlib

app = typer.Typer(chain=True)
init = typer.Typer(name="init")
gist = typer.Typer(name="gist")
app.add_typer(init)
nox.options.sessions = []

from .__init__ import *

task_file = pathlib.Path(__file__).parent / "__init__.py"


class Complete(Exception):
    """an exception to signify the program is complete"""


@app.command()
def add(ctx: typer.Context):
    """add something to project"""
    # i don't know what this does yet, but it is git stuff likely
    nox.options.session += ["add"]


@app.command()
def configure(ctx: typer.Context, lint: bool = True, python="infer"):
    """write/update configuration files for a project."""
    options.python = python
    nox.options.sessions += ["configure"]


@app.command()
def develop(
    ctx: typer.Context,
    conda: bool = False,
):
    """develop a project"""
    __import__("nox").options.sessions += ["develop"]
    conda and nox.session(venv_backend="conda")(develop)


@app.command()
def install(ctx: typer.Context, conda: bool = False):
    """install a project"""
    nox.options.sessions += ["install"]
    conda and nox.session(venv_backend="conda")(install)


@app.command()
def build(ctx: typer.Context, conda: bool = False):
    """build a project"""
    nox.options.sessions += ["build"]
    conda and nox.session(venv_backend="conda")(build)


@app.command()
def docs(ctx: typer.Context, watch: bool = False):
    """build the documentation"""
    options.watch = watch
    options.docs = "jb"
    nox.options.sessions += ["docs"]


@app.command()
def lint(ctx: typer.Context):
    """lint the project"""
    nox.options.sessions += ["lint"]


@app.command()
def test(ctx: typer.Context, stubs: bool = False):
    """test the project"""
    options.generate_types = stubs
    nox.options.sessions += ["test"]


@app.command()
def blog(ctx: typer.Context):
    """transform the blog to html"""
    nox.options.sessions += ["blog"]


@app.command()
def doit(ctx: typer.Context, file: pathlib.Path = ""):
    "run a file of doit tasks in a closed nox environment."
    nox.options.session += ["doit"]
    # need to pass extra arguments through the cli.


def nox_runner(module):
    """a wrapped nox runner specifically for qpub.

    it works off a module loaded into the namespace already
    rather than a static file.
    """

    import sys, nox

    argv = sys.argv
    sys.argv = [__file__]
    ns = nox._options.options.parse_args()
    sys.argv = argv
    # run the tasks ourselves to avoid switching directories

    nox.tasks.merge_noxfile_options(module, ns)
    manifest = nox.tasks.discover_manifest(module, ns)
    nox.tasks.filter_manifest(manifest, ns)
    nox.tasks.verify_manifest_nonempty(manifest, ns)
    results = nox.tasks.run_manifest(manifest, ns)
    nox.tasks.print_summary(results, ns)
    nox.tasks.create_report(results, ns)
    return nox.tasks.final_reduce(results, ns)


# the typer cli
# we use typer/click to compose the top-level cli.
# these commands configure the execution state for the nox sessions.


# isolated nox sessions
# nox sessions are used to shell out commands run in specific, task-oriented virtual environment


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
    session.run(*"pip install colorlog".split())
    session.run(*"pip install .[test]".split())
    if options.generate_types:
        session.run(*"pip install monkeytype".split())
        session.run(*"monkeytype run -m pytest".split())
    else:
        session.run(*"pytest".split())


@nox.session(reuse_venv=True)
def docs(session):
    session.install(
        *"jupyter-book doit GitPython depfinder aiofiles appdirs typer nox pathspec requests-cache tomlkit".split()
    )
    if options.watch:
        session.run(*f"python -m doit auto --dir . --file {task_file} -s html".split())
    else:
        session.run(*f"python -m doit --dir . --file {task_file} -s html".split())


@nox.session(reuse_venv=True)
def blog(session):
    session


@nox.session(reuse_venv=True)
def configure(session):
    """produce the configuration for different distributions."""
    session.install(
        *"doit GitPython depfinder aiofiles appdirs typer nox pathspec requests-cache tomlkit".split()
    )
    session.run(
        *f"""python -m doit --dir . --file {task_file} lint docs python gitignore""".split(),
        env=options.dump(),
    )


@nox.session(reuse_venv=True)
def doit(session):
    """produce the configuration for different distributions."""
    session.install(*"doit".split())
    session.install(*project.get_requires())
    file = project.fs.get_module_name()[1]
    session.run(
        *f"""python -m doit --dir . --file {file} """.split() + session.posargs,
        env=options.dump(),
    )


def main():
    try:
        # run the typer application to configure the nox sessions
        # some commands may raise to indicate completed.
        app()
    except SystemExit as exception:
        # run the nox sessions that were configured.
        if nox.options.sessions:
            if "configure" not in nox.options.sessions:
                nox.options.sessions.insert(0, "configure")
            raise SystemExit(nox_runner(locals()))
        raise exception


if __name__ == "__main__":
    main()
    assert (
        False
    ), "We should never have reached here, because the program will have raised."
