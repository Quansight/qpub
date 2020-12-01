"""noxfile.py"""

import nox


@nox.session(reuse_venv=True)
def lint(session):
    session.install("pre-commit")
    session.run(*"pre-commit run --all-files".split())


@nox.session(reuse_venv=True)
def pytest(session):
    print("running nox")
    session.install(
        *"pytest pytest-sugar pytest-github-actions-annotate-failures".split()
    )
    session.run("pytest")