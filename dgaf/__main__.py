"""__main__.py"""
import typer
import nox
import pathlib

app = typer.Typer(chain=True)
nox.options.sessions = []

from .__init__ import *

task_file = pathlib.Path(__file__).parent / "__init__.py"


@app.command()
def configure(ctx: typer.Context, lint: bool = True):
    """write/update configuration files for a project."""
    nox.options.sessions += ["configure"]


@app.command()
def develop(ctx: typer.Context, conda: bool = False):
    """develop a project"""
    nox.options.sessions += ["develop"]
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
def docs(ctx: typer.Context):
    """build the documentation"""
    nox.options.sessions += ["docs"]


@app.command()
def lint(ctx: typer.Context):
    """lint the project"""
    nox.options.sessions += ["lint"]


@app.command()
def test(ctx: typer.Context):
    """test the project"""
    nox.options.sessions += ["test"]


@app.command()
def blog(ctx: typer.Context):
    """transform the blog to html"""
    nox.options.sessions += ["blog"]


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
    session.run(*"pytest".split())


@nox.session()
def docs(session):
    session.install(*"jupyter-book".split())
    session.run(
        *"jupyter-book build .  --path-output docs --toc docs/_toc.yml --config docs/_config.yml".split()
    )


@nox.session()
def blog(session):
    session


@nox.session(reuse_venv=True)
def configure(session):
    """produce the configuration for different distributions."""
    session.install(
        *"doit GitPython depfinder aiofiles appdirs typer nox requests-cache tomlkit".split()
    )
    session.run(
        *f"""python -m doit --dir . --file {task_file} lint docs python""".split()
    )


def main():
    try:
        app()
    except SystemExit as exception:
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
