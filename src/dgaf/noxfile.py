"""nox sessions that execute command line actions in virtual environments.

this document encodes common practices for command line utilities to package,
document, test, and lint software. nox allows us to control the environments
each utility operates within.
"""

import nox
import sys
import importlib
import functools
import shutil
import pathlib
import contextlib

Path = type(pathlib.Path())


def run_in_nox():
    return sys.argv[0].endswith(("bin/nox", "nox/__main__.py"))


try:
    from .dodo import options, File, PYPROJECT_TOML, Project, ENVIRONMENT_YAML
except ImportError as e:
    # when we invoke this file from nox it cannot naturally import files. this block loads the task file from teh specification.
    if run_in_nox():
        dodo = importlib.util.module_from_spec(
            importlib.util.spec_from_file_location(
                "dodo", Path(__file__).parent / "dodo.py"
            )
        )
        dodo.__loader__.exec_module(dodo)
        locals().update(
            {
                k: getattr(dodo, k)
                for k in """options File PYPROJECT_TOML Project ENVIRONMENT_YAML""".split()
            }
        )
    else:
        raise e

nox.options.default_venv_backend = shutil.which("conda") and "conda"
nox.options.envdir = options.cache / ".nox"

_add_requirements = """depfinder aiofiles appdirs
json-e flit poetry requests-cache tomlkit""".split()
_core_requirements = """doit GitPython pathspec importlib_metadata""".split()
_interactive_requirements = """""".split()

# patches to use mamba with nox
if "_run" not in locals():
    _run = nox.sessions.Session._run


def conda_install(dir, session):
    if not nox.options.default_venv_backend == "conda":
        return []

    no_deps = ["--no-deps"]

    if not (File(dir) / ENVIRONMENT_YAML).exists():
        session.run(*f"python -m dgaf.tasks {ENVIRONMENT_YAML}".split())
    env = (File(dir) / ENVIRONMENT_YAML).load()
    c, p = [], []
    for dep in env.get("dependencies", []):
        if isinstance(dep, str):
            c += [dep]
        elif isinstance(dep, dict):
            p = dep.pop("pip")
    if c:
        session.conda_install(*"-c conda-forge".split(), *c)

    p and session.install(*p, *no_deps)
    return no_deps


def run_mamba(self, *args, **kwargs):
    if args[0] == "conda":
        args = ("mamba",) + args[1:]
    return _run(self, *args, **kwargs)


@contextlib.contextmanager
def mamba_context(session):
    global _run
    session.conda_install("mamba")
    nox.sessions.Session._run = run_mamba
    yield session
    nox.sessions.Session._run = _run


def session(callable):
    nox.session(callable)
    if options.conda and options.mamba:

        @functools.wraps(callable)
        def main(session):
            with mamba_context(session) as session:
                return callable(session)

        return main
    return callable


@session
def tasks(session):
    """tasks for configuring different forms of projects.

    the tasks write to common configuration convetions like pyproject.toml"""
    session.install(*_core_requirements, *_add_requirements)
    session.run(
        *f"""doit -f {Path(__file__).parent / "dodo.py"}""".split(),
        *options.tasks,
        *session.posargs,
        env=options.dump(),
    )


@session
def install(session):
    no_deps = init_conda_session(dir, session)
    pyproject = (File() / PYPROJECT_TOML).load()
    # backend = pyproject.get("build-system", {}).get("build-backend", None)
    if options.dev:
        if options.pip:
            session.run(*"pip install -e.".split(), *no_deps)
        else:
            session.install("flit")
            session.run(*"flit install -s".split(), *no_deps)
    else:
        if options.pip:
            session.run(*"pip install .".split(), *no_deps, env=options.dump())
        else:
            session.install("flit")
            session.run(*"flit install -s".split())


@session
def test(session):
    if options.install:
        install(session)
    if options.monkeytype:
        session.install("monkeytype")
        session.run(*"monkeytype run -m pytest".split(), *options.posargs)
    else:
        session.run("pytest", *options.posargs)


@session
def lint(session):
    session.install("pre-commit")
    session.run(*"pre-commit run --all-files".split(), success_codes=[0, 1])


@session
def uninstall(session):
    extra = ("-y",) if options.confirm else tuple()
    session.run(*"pip uninstall".split(), *extra, Project().get_name())


@session
def docs(session):
    no_deps = init_conda_session(dir, session)

    session.install(".[doc]", "--no-deps")
    session.install(options.dgaf + "[core]", *no_deps)
    if options.watch:
        session.run(
            *f"python -m dgaf.tasks auto --dir . -s html".split(),
            env=options.dump(),
            external=True,
        )
    else:
        session.run(
            *f"python -m dgaf.tasks -s jupyter_book".split(), env=options.dump()
        )
    options.pdf
    if options.serve:
        session.run(*f"python -m http.server -d docs/_build/html".split())


def init_conda_session(dir, session):

    if not options.conda:
        return []
    no_deps = ["--no-deps"]

    if not (File(dir) / ENVIRONMENT_YAML).exists():
        session.run(*f"python -m dgaf.tasks {dir / ENVIRONMENT_YAML}".split())
    env = (File(dir) / ENVIRONMENT_YAML).load()
    c, p = [], []
    for dep in env.get("dependencies", []):
        if isinstance(dep, str):
            c += [dep]
        elif isinstance(dep, dict):
            p = dep.pop("pip")
    if c:
        session.conda_install(*"-c conda-forge".split(), *c)

    p and session.install(*p, *no_deps)
    return no_deps
