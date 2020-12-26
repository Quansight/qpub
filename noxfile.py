#!/usr/bin/env -vS nox -f

"""dgaf uses nox to bootstrap itself.

the top-level nox file bootstraps dgaf for development and ci.
"""

import nox

nox.options.sessions = ["develop"]

session = nox.session(python=False)


@session
def develop(session):
    session.run(*"python -m dgaf develop".split())


@session
def test(session):
    session.install(".[test]")
    # dgaf runs the tests in a virutal environment
    if "type" in session.posargs:
        session.install("monkeytype")
        yuck = session.posargs.pop(session.posargs.index("type"))
        session.run(*"monkeytype run -m pytest".split() + list(session.posargs))
    else:
        session.run(*"pytest".split() + list(session.posargs))


@session
def docs(session):
    session.run(*"python -m dgaf docs".split())


@session
def install(session):
    session.install(*"pytest setuptools --upgrade".split())
    session.run(*"python -m dgaf install".split())


@session
def binder(session):
    session.run(*"python -m dgaf develop".split())
    session.run(*"dgaf docs".split())
    session.run(*"dgaf test".split())
