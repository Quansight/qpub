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
    session.install(".")
    # dgaf runs the tests in a virutal environment
    session.run(*"python -m dgaf lint test".split())


@session
def docs(session):
    session.run(*"python -m dgaf docs".split())


@session
def install(session):
    session.run(*"python -m dgaf install".split())


@session
def binder(session):
    session.run(*"python -m dgaf develop".split())
    session.run(*"dgaf docs".split())
    session.run(*"dgaf test".split())
