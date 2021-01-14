# `dgaf` templates

`dgaf` vendors in configuration with the [`json-e`][json-e] (jinja in data structures.) format.

one of the reasons `dgaf` is that across configuration files there is significant overlap information. `dgaf` infers information is passed to json-e for configuration.

## packaging

packaging conventions in python are in are flux, `dgaf` helps manage the transition between configurations by encoding multiple standards into its inference engine.

### pyproject

* `flit.json` - __[flit]__ is a simple way to put Python packages and modules on PyPI.
* `poetry.json` - __[poetry]__ is a python packaging and dependency management
* `setuptools.toml.json` - the build backend for __[setuptools]__

### declarative `setup.cfg`

* `setuptools.cfg.json` - python packaging, the old way with __[setuptools]__

## configuration


### pyproject

`dgaf` consistently uses `pyproject.toml` for project packaging and configuration when possible

* `pytest.json` - __[pytest]__ is the python testing standard
* `flakehell.json` - __[flakehell]__ simplifies linting configuration

### other

* `precommit.json` - __[precommit]__ configuration, we don't install the hooks, but use the linting machinery
* `_config.json` - __[jupyter_book]__ documentation configuration
* `config.json` - __[nikola]__ blog configuration, then translated to python

## ignore files

managing ignored content in `qpub` is critical. some development suffer in performance and efficacy when we don't properly exclude content. for example, in testing, `pytest` may discover files or, in documentation, `sphinx` may include files that that aren't part of the project. by managing the ignored files, `qpub` can configure the proper conventions to exclude.

we vendor in github's [gitignore] files, and couple them with [`pathspec`][pathspec], to detect the excluded contents. there are 3 ignore files included:

* `JupyterNotebooks.gitignore`
* `Nikola.gitignore`
* `Python.gitignore`

[poetry]: https://python-poetry.org/
[flit]: https://flit.readthedocs.io/
[precommit]: https://pre-commit.com/
[flakehell]: https://flakehell.readthedocs.io/
[pytest]: https://docs.pytest.org/
[setuptools]: https://setuptools.readthedocs.io/en/latest/userguide/declarative_config.html
[json-e]: https://pypi.org/project/json-e/
[gitignore]: https://github.com/github/gitignore/
[pathspec]: https://pypi.org/project/pathspec/
[jupyter_book]: https://jupyterbook.org/
[nikola]: https://getnikola.com/