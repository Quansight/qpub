# `dgaf` source

`dgaf` is designed from existing conventions within a [src directory](https://hynek.me/articles/testing-packaging/) configuration. the `dgaf` source has modules for:

* `__init__.py` makes it a python project and usable interactively

    it defines the docstring and version to comply with the flit convention.

* `__main__.py` defines the CLI for `dgaf`

    `dgaf` is an composite [`typer`][typer] api overtop of `nox` sessions and `doit` tasks; it provides conveniences for using these tools

* `dodo.py` id a convention for [doit] tasks

    [doit] is reliable make-like interface in python. it provides `dgaf` with file watching abilities and task introspection from the command line

* `noxfile.py` define `nox` sessions for the `dgaf` tasks to run within

    [nox] is a tool for programmatically managing environments in python. it can manage python and conda environments. it shields `dgaf`s environment from the development environment.

## standalone usage

those experienced with `doit or nox` can invoke tasks or sessions their standard command line interfaces.

### using `nox` standalone

    nox -f src/dgaf/noxfile.py -l

for more information, see the [`nox` command line usage documentation](https://nox.thea.codes/en/stable/usage.html).

### using `doit` standalone

`dgaf` does not install `doit` the root environment.

    doit -f src/dgaf/dodo.py list

for more information, see the [`doit` command line usage documentation](https://pydoit.org/cmd_run.html).

[doit]: https://pydoit.org/
[nox]: https://nox.thea.codes/
[typer]: https://typer.tiangolo.com/
