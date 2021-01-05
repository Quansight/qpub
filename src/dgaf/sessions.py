"""nox sessions that execute command line actions in virtual environments.

this document encodes common practices for command line utilities to package,
document, test, and lint software. nox allows us to control the environments
each utility operates within.
"""

import nox
from .__init__ import *

_add_requirements = """depfinder aiofiles appdirs
json-e flit poetry requests-cache tomlkit""".split()
_core_requirements = """doit GitPython pathspec""".split()
_interactive_requirements = """""".split()


@nox.session
def add(session):
    session.install(*_core_requirements, *_add_requirements)
    if options.interactive:
        session.install(*_interactive_requirements)
        session.run(
            *"python -m dgaf.interactive".split(), *options.tasks, env=options.dump()
        )
    else:
        # nox is never imported when the tasks are run
        session.install(options.dgaf)
        session.run(*"python -m dgaf.tasks".split(), *options.tasks, env=options.dump())


@nox.session
def develop(session):
    no_deps = util.init_conda_session(dir, session)

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
    no_deps = util.init_conda_session(dir, session)

    session.run(*"pip install .".split(), *no_deps, env=options.dump())


@nox.session
def test(session):
    no_deps = util.init_conda_session(dir, session)

    session.install(".[all]", *no_deps)
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
    no_deps = util.init_conda_session(dir, session)

    session.install(options.dgaf + "[core]", "flit", *no_deps)
    if options.watch:
        session.run(
            *f"python -m dgaf.tasks auto --dir . -s html".split(), env=options.dump()
        )
    else:
        session.run(
            *f"python -m dgaf.tasks -s jupyter_book".split(), env=options.dump()
        )
    options.pdf
    if options.serve:
        session.run(*f"python -m http.server -d docs/_build/html".split())
