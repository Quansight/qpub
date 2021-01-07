# `dgaf` source

`dgaf` is designed from existing conventions.
the `dgaf` source has modules for:

* `__init__.py` defines the base `Chapter and Project` objects
* `__main__.py` defines the CLI for `dgaf`
* `dodo.py` defines [doit] tasks for updating configurations and other files.
* `noxfile.py` define `nox` sessions for the `dgaf` tasks to run within.

`dodo.py` and `noxfile.py` can be executed using their standard cli conventions.
