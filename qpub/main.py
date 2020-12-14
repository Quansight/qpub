"""main.py"""
import types
from . import options
import nox.__main__
import typer

app = typer.Typer(
    chain=True, no_args_is_help=True, help="q(uick)pub(lishing) of python projects."
)


_ORDERING = (
    "bootstrap",
    "lint",
    "poetry",
    "flit",
    "setuptools",
    "local",
    "develop",
    "build",
    "install",
    "docs",
    "blog",
    "test",
)


def with_options_context(callable):
    import functools

    @functools.wraps(callable)
    def wraps(ctx, *args, **kwargs):
        if all(x in ctx.params for x in "poetry flit setuptools".split()):
            if not any(map(ctx.params.get, "poetry flit setuptools".split())):
                ctx.params["flit"] = True
        [setattr(options, k, v) for k, v in ctx.params.items()]
        return callable(ctx, *args, **kwargs)

    return wraps


@app.command()
def requires():
    """display the requirements for the project"""
    from .base import Project

    print("\n".join(Project().get_requires()))
    raise SystemExit(0)


@app.command()
def lint():
    """lint a project

    qpub generates .pre-commit-config.yaml, the pre-commit convention,
    configurations based on the contents of project. it codifies best
    practices from experiences with different tools.

    the configuration discovery is based off suffixes of the contents of the repository.
    """
    nox.options.sessions += ["lint"]


@app.command()
@with_options_context
def local(
    ctx: typer.Context,
    conda: bool = typer.Option(False, help="install into a conda environment."),
):
    """install dependencies into the environment with conda/pip"""
    nox.options.sessions += ["local"]


@app.command()
@with_options_context
def develop(
    ctx: typer.Context,
    poetry: bool = typer.Option(False, help="develop with poetry"),
    flit: bool = typer.Option(False, help="develop with flit"),
    setuptools: bool = typer.Option(False, help="develop with setuptools"),
):
    """install a project in edittable mode.

    qpub supports three conventions for installing projects:

    1. poetry
    2. flit
    3. setuptools

    """
    nox.options.sessions += [
        poetry and "poetry" or flit and "flit" or setuptools and "setuptools" or "local"
    ]

    options.install = False
    options.develop = bool(poetry or flit or setuptools)


@app.command()
@with_options_context
def install(
    ctx: typer.Context,
    poetry: bool = typer.Option(False, help="install with poetry"),
    flit: bool = typer.Option(False, help="install with flit"),
    setuptools: bool = typer.Option(False, help="install with setuptools"),
):
    """install a project into site-packages."""
    nox.options.sessions += [
        poetry
        and "poetry"
        or flit
        and "flit"
        or setuptools
        and "setuptools"
        or "poetry"
    ]
    options.install = True


@app.command()
@with_options_context
def build(
    ctx: typer.Context,
    pep517: bool = typer.Option(
        True, help="build using the pyproject.toml pep 517 convention."
    ),
):
    """build the python project.

    use either the new pep517 building convention, or the older setuptools conventions.
    """
    nox.options.sessions += ["build"]


@app.command()
@with_options_context
def docs(
    ctx: typer.Context,
    pdf: bool = typer.Option(False, help="build a pdf version of the document"),
    html: bool = typer.Option(False, help="build an html version of the document"),
    watch: bool = typer.Option(False, help="live reload the documentation"),
):
    """build project documentation."""
    nox.options.sessions += ["docs"]


@app.command()
def blog():
    """build a blog from the content."""
    nox.options.sessions += ["blog"]


@app.command()
def test():
    """test the project.


    test the project with pytest"""
    nox.options.sessions += ["test"]


def main(exit=0):
    """the main cli function for qpub."""
    from . import noxfile, util

    # noxfile has the specifications for the sessions we desire to run.
    # initialize the sessions options in the nox configuration
    # https://nox.thea.codes/en/stable/config.html?highlight=options#modifying-nox-s-behavior-in-the-noxfile
    nox.options.sessions = nox.options.sessions or []

    # run the typer application that chains together the sessions we desire to run.
    typer.main.get_command(app).main(standalone_mode=False)

    # if any sessions exist then we execute them with our own nox runner.
    if nox.options.sessions:
        nox.options.sessions = sorted(nox.options.sessions, key=_ORDERING.index)
        exit = SystemExit(util.nox_runner(noxfile))

    SystemExit(exit)
