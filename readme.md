# `qpub` - automating publishing workflows

sphinx as the engine for docs
tox/pytest as the engine for tests
poetry as the engine for environments

`qpub` works with files

`qpub` is make to publish artifacts from python source including notebooks, markdown, rst, and python files. `qpub` focuses on ambiguous, nascent content; it provides popular opinions for representing the content as tests, documentation, development and installation files. `qhub` generates complete _slow_ configuration files from the partial information within the underlying _fast_ content.

* Poetry is a tool for dependency management and packaging in Python. It allows you to declare the libraries your project depends on and it will manage (install/update) them for you.
* doit comes from the idea of bringing the power of build-tools to execute any kind of task


conventions for packaging and testing require complete information to configure their outcomes. often the information underlying the information for configurations.

the `qpub` api is designed to provide consistent command line interactions from local, remote, and CI development.

## motivation from python packaging.


`dgaf` uses repository information to generate _slow_ configuration files from partial information stored from _fast_ files.

the git repository retains the context of a project's changes in entropy over time. within a programming ecosystem there are canonical conventions that allow communities to identify each other. the conventions retain cultural histories of the software and become difficult to change. meanwhile, content uses convention as technology to convey computational concepts.

the kinetics of conventions are slower than the those of content; generally the the context is fixed unless divise organizational events occur.

        d(context)/dt << d(convention)/dt << d(content)/dt

a meeting, assembly; an agreement

conventions are coherent interfaces between literature and software.

# deathbeds generalized automation framework

the deathbeds generalized automation framework provides opinionated tools for publishing python. typically, python tools require complete configurations to acheive their goals. configuration metadata tends to be redudant across different files

`dgaf` relies on configurations in the `"pyproject.toml"` too infer installation and development environments;
projects abiding the `"pyproject.toml"` convention can be this _awesome list_.

`dgaf` is a consistent CLI for publishing different forms of content in different environments (eg. local develop/install, github actions testing, publishing to github pages, deploying binders). it encodes different opinions for building, installing, testing, and documenting applications. tool churn is real challenge for open source python development. `dgaf` tries to aggregate best present and future practices for publishing different code artifacts.

`dgaf` is good for small project where content is :crown:. for older projects, `dgaf` may be a good test for transitioning old build chains to modern python conventions.

## what does `dgaf` do?

`dgaf` infers environment conditions using system variables and files in a git repo. from these partial initial conditions `dgaf` expands configuration files for different publishing to aid produces different forms of content. content can include python, rst, markdown, or


 works across different environments like conda, pip, and tox. it can infer these environment conditions from partial information in canonical configuration files and tracked content. with the configuration files, it can execute difference services for publishing facets of the project.

some features of `dgaf` are:

* `dgaf infer` discovers dependencies and updates the requirements in different configuration files.
* `dgaf setup` installs the environment dependencies
* `dgaf develop` makes a development package of the project
* `dgaf install` installs the project.
* `dgaf test` run the tests
* `dgaf docs` generates a table of contents and builds the docs with jupyter book
* `dgaf postbuild` builds a development version of the package for binder

### extra configuration

`dgaf` will merge and append to existing configurations in smart ways. extra configuration can be provided to any tool by seeding the correct configuration file with partial information.

### `dgaf` flags

`dgaf` uses the `.gitignore` files to control different features. a default `dgaf` `.gitignore` will specify the configuration files that `dgaf` generates; a specific process is ignored by prepending an `!` to a configuration

```bash
tox.ini # generates tox configuration
!tox.ini # skips tox configuration
```

## requirements

`dg     af` requires a git repository with content.
# development


https://mozillascience.github.io/working-open-workshop/contributing/
https://gist.github.com/bollwyvl/f6aac8d4e68e5594fad2ae7a3cacc74b
https://gist.github.com/tonyfast/f74eb42f2a998d8e428a752ceb0cb1d1
https://github.com/carlosperate/awesome-pyproject
https://twitter.com/SourabhSKatoch/status/1330068683222183936?s=20
https://setuptools.readthedocs.io/en/latest/userguide/declarative_config.html
https://pre-commit.com/hooks.html
https://github.com/nbQA-dev/nbQA
https://docs.python.org/3/distutils/configfile.html
https://pyscaffold.org/en/latest/features.html

should we pre install a bunch of different pytest opinions?

[github actions]: #
https://github.com/David-OConnor/pyflow