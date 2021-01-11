"""nox sessions that execute command line actions in virtual environments.

this document encodes common practices for command line utilities to package,
document, test, and lint software. nox allows us to control the environments
each utility operates within.
"""

import contextlib
import functools
import importlib
import itertools
import os
import pathlib
import shutil
import sys

import nox

Path = type(pathlib.Path())


def run_in_nox():
    return sys.argv[0].endswith(("bin/nox", "nox/__main__.py"))


try:
    from .dodo import ENVIRONMENT_YAML, PYPROJECT_TOML, File, Project, options
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

if "_install" not in locals():
    _install = nox.sessions.Session.install


def run(session, *args, **kwargs):
    if "mamba" == options.install_backend:
        if args[0] == "conda":
            args = "mamba", *args[1:]
    session._runner.global_config.last_result = _run(session, *args, **kwargs)
    return session._runner.global_config.last_result


nox.sessions.Session._run = run


def session_install(session, *args, **kwargs):
    """a general installer for conda and pip. it prefers conda,
    and defers to pip"""
    mamba, conda = (
        options.install_backend == "mamba",
        options.install_backend == "conda",
    )
    pip = []
    if len(args) == 1:
        args = tuple(itertools.chain(*map(str.split, args)))

    pip = [x for x in args if x.startswith(".")]
    args = [x for x in args if x not in pip]

    if conda:
        _run = type(session).run

        type(session).run = run

        try:
            session.conda_install(*args, **kwargs, silent=True, success_codes=[0, 1])
            pip = get_unfound_packages(session._runner.global_config.last_result)
            if pip:
                args = [x for x in args if x not in pip]
                session.conda_install(*args, **kwargs)

        finally:
            type(session).run = _run
    else:
        pip = args
    no_deps = ["--no-deps"] if options.install_backend in {"conda", "mamba"} else []
    if pip:
        session_install_pip(session, *pip, *no_deps)


def session_install_pip(session, *args, **kwargs):
    _install(session, *args, **kwargs)


nox.sessions.Session.install = session_install

session = nox.session


def get_unfound_packages(str):
    collect = False
    packages = []
    for line in str.splitlines():
        if line.startswith("PackagesNotFoundError: "):
            collect = True
            continue
        if not collect:
            continue
        if collect:
            if line.strip():
                packages.append(line.strip().lstrip("-").strip())
        if packages and not line.strip():
            return packages
    return packages


@session
def tasks(session):
    """tasks for configuring different forms of projects.

    the tasks write to common configuration convetions like pyproject.toml"""
    options.install_backend = "pip"
    session.install(*_core_requirements, *_add_requirements)
    session.run(
        "doit",
        f"""--file={Path(__file__).parent / "dodo.py"}""",
        f"""--dir={os.getcwd()}""",
        *options.tasks,
        env=options.dump(),
        silent=False,
    )


@session
def install(session):
    no_deps = [] if options.install_backend in {"conda", "mamba"} else []
    if options.dev:
        if options.pip_only:
            session.run(*"pip install -e.".split(), *no_deps)
        else:
            session_install_pip(session, "flit")
            session.run(*"flit install -s".split(), *no_deps)
    else:
        if options.pip_only:
            session.run(*"pip install .".split(), *no_deps, env=options.dump())
        else:
            session_install_pip(session, "flit")
            session.run(*"flit install -s".split())


@session
def test(session):
    if options.install:
        install(session)
    if options.monkeytype:
        session_install_pip("monkeytype")
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
    options.install_backend = "pip"
    session.install(*_core_requirements, "flit", "packaging")
    if options.dgaf == Path:
        session_install(session, options.dgaf + "[doc]")
    if options.watch:
        session.run(
            "doit",
            f"""--file={Path(__file__).parent / "dodo.py"}""",
            f"""--dir={os.getcwd()}""",
            "auto",
            "jupyter_book",
            env=options.dump(),
            silent=False,
        )
    else:
        session.run(
            "doit",
            f"""--file={Path(__file__).parent / "dodo.py"}""",
            f"""--dir={os.getcwd()}""",
            "jupyter_book",
            env=options.dump(),
            silent=False,
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
