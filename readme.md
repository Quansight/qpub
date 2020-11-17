# deathbeds generalized automation framework

the deathbeds generalized automation framework provides opinionated tools for publishing python. `dgaf` is an opinionated command line interface for building, installing, testing, and documenting applications. tool churn is real challenge for open source python development. `dgaf` tries to aggregate best present and future practices for publishing different code artifacts.

## what does `dgaf` do?

`dgaf` works across different environments like conda, pip, and tox. it can infer these environment conditions from partial information in canonical configuration files and tracked content. with the configuration files, it can execute difference services for publishing facets of the project.

some features of `dgaf` are:

* `dgaf infer` discovers dependencies and updates the requirements in different configuration files.
* `dgaf preinstall` installs the environment dependencies
* `dgaf develop` makes a development package of the project
* `dgaf install` installs the project.
* `dgaf test` run the tests
* `dgaf docs` generates a table of contents and builds the docs with jupyter book
* `dgaf postbuild` builds a development version of the package for binder

### extra configuration

`dgaf` will merge and append to existing configurations in smart ways. extra configuration can be provided to any tool by seeding the correct configuration file with partial information.

### `dgaf` flags

`dgaf` uses the `.gitignore` files to control different features. a default `dgaf` `.gitignore` will specify the configuration files that `dgaf` generates; a specific process is ignored by prepending an `!` to a configuration

    tox.ini # generates tox configuration
    !tox.ini # skips tox configuration

## requirements

`dgaf` requires a git repository with content.
# development

    def task_dev():

install dgaf in development mode.

        return dict(
            actions="""
    pip install -rrequirements.txt
    python -m dgaf infer develop
        """.strip().splitlines(), 
            file_dep=["requirements.txt"],
            uptodate=[False]
        )


    def task_preinstall():

install the built dgaf this is used in [github actions] for testing this package on mac, windows, and linux.

        return dict(
            actions="""
    pip install -rrequirements.txt
    python -m dgaf infer preinstall
        """.strip().splitlines(), 
            file_dep=["requirements.txt"],
            uptodate=[False]
        )

https://mozillascience.github.io/working-open-workshop/contributing/
https://gist.github.com/bollwyvl/f6aac8d4e68e5594fad2ae7a3cacc74b
https://gist.github.com/tonyfast/f74eb42f2a998d8e428a752ceb0cb1d1

should we pre install a bunch of different pytest opinions?

[github actions]: #