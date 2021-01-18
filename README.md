# qpub - q(uick) publishing of python projects

`qpub` is an opinioned collection of conventional tasks for distributing python packages, tests, and documentation. `qpub` is a consistent CLI for publishing different forms of content in different environments (eg. local develop/install, github actions testing, publishing to github pages, deploying binders). it encodes different opinions for building, installing, testing, and documenting applications. tool churn is real challenge for open source python development. `qpub` tries to aggregate best present and future practices for publishing different code artifacts.

`qpub` is good for small project where content is :crown:. for older projects, `qpub` may be a good test for transitioning old build chains to modern python conventions.

## what does `qpub` do?

`qpub` infers environment conditions using system variables and files in a git repo. from these partial initial conditions `qpub` expands configuration files for different publishing to aid produces different forms of content. content can include python, rst, markdown, or notebooks.

some features of `qpub` are:

* `qpub infer` discovers dependencies and updates the requirements in different configuration files.
* `qpub setup` installs the environment dependencies
* `qpub develop` makes a development package of the project
* `qpub install` installs the project.
* `qpub test` run the tests
* `qpub docs` generates a table of contents and builds the docs with jupyter book
* `qpub postbuild` builds a development version of the package for binder

### extra configuration

`qpub` will merge and append to existing configurations in smart ways. extra configuration can be provided to any tool by seeding the correct configuration file with partial information.


## requirements

`qpub` requires a git repository with content.

# development

the `nox` file encodes common development tasks.

https://mozillascience.github.io/working-open-workshop/contributing/
https://gist.github.com/bollwyvl/f6aac8d4e68e5594fad2ae7a3cacc74b
https://gist.github.com/tonyfast/f74eb42f2a998d8e428a752ceb0cb1d1

should we pre install a bunch of different pytest opinions?

[github actions]: #
`