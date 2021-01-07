"""nox sessions that execute command line actions in virtual environments.

this document encodes common practices for command line utilities to package,
document, test, and lint software. nox allows us to control the environments
each utility operates within.
"""

import nox
import sys
import importlib
import pathlib

Path = type(pathlib.Path())


def run_in_nox():
    print(sys.argv)
    return sys.argv[0].endswith("bin/nox")


try:
    from .dodo import options, File, PYPROJECT_TOML, Project, ENVIRONMENT_YAML
except ImportError as e:
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


_add_requirements = """depfinder aiofiles appdirs
json-e flit poetry requests-cache tomlkit""".split()
_core_requirements = """doit GitPython pathspec""".split()
_interactive_requirements = """""".split()


@nox.session
def add(session):
    session.install(*_core_requirements, *_add_requirements)
    # nox is never imported when the tasks are run
    session.install(options.dgaf)
    session.run(
        *f"""doit -f {Path(__file__).parent / "dodo.py"}""".split(),
        *options.tasks,
        env=options.dump(),
    )


@nox.session
def develop(session):
    no_deps = init_conda_session(dir, session)

    pyproject = (File() / PYPROJECT_TOML).load()
    backend = pyproject.get("build-system", {}).get("build-backend", None)

    if backend == "flit_core.buildapi":
        # install flit, the flit way
        session.install("flit")
        session.run(*"flit install -s".split())
        return

    session.run(*"pip install -e.".split(), *no_deps)


@nox.session
def install(session):
    no_deps = init_conda_session(dir, session)

    session.run(*"pip install .".split(), *no_deps, env=options.dump())


@nox.session
def test(session):
    no_deps = init_conda_session(dir, session)

    session.install(".[test]")
    if options.monkeytype:
        session.install("monkeytype")
        session.run(
            *"monkeytype run -m pytest".split(), *options.posargs, *session.posargs
        )
    else:
        session.run("pytest", *options.posargs, *session.posargs)


@nox.session
def lint(session):
    session.install("pre-commit")
    session.run(*"pre-commit run --all-files".split(), success_codes=[0, 1])


@nox.session
def uninstall(session):
    extra = ("-y",) if options.confirm else tuple()
    session.run(*"pip uninstall".split(), *extra, Project().get_name())


@nox.session
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
