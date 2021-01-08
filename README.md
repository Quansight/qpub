# `qpub` - literate packaging commands

in the python world, there are conventional forms and tools for distributing packages, tests, and documentation. `qpub` organizes these opinions and system specific conditions into a consistent command line interface. the unique affordance of `qpub` is that it can infer complete configurations from the contents of project; it can produce packaging, environment, documentation, and testing configuration to name a few.

with `dgaf` you have the freedom to restructure your project as different forms. `dgaf` will infer and configure your project.

## quickstart

the quickest way to begin is to:

```bash
# have some content in a directory
pushd some_place_with_content
# install dgaf
pip install dgaf
# run the add command to configure the project
dgaf add
```

## `dgaf sessions`

`dgaf sessions` reveals the `nox` cli for designing virtual and developer environments.

    dgaf sessions -h # reveals the nox cli.

## `dgaf tasks`

`dgaf tasks` reveals the `doit` for managing the changes to files. by choosing doit tasks we can choose to trigger watcher events based on file system changes.

## `dgaf add`

`dgaf add` runs `dgaf add lint py docs blog` by default and will:

1. configure a `".pre-commit-config.yaml"` to use `pre_commit` for linting and formatting.
2. configure a python distribution in `"pyproject.toml"` using `flit, poetry or setuptools` backends.
3. configure a table of contents, `"docs/_toc.yml"` for the `jupyter_book` documentation
4. create the documentation configuration file

```bash
dgaf add actions readthedocs postbuild conda requirements
```

all of the configuration files are created by inferring information from the file system or github repository. `dgaf` can generate configuration for other tools like readthedocs, github actions, conda, pip.

## `dgaf run`

`dgaf` can run the services that it knows how to configure. the tasks are executed in virtual environments to avoid polluting your environment.


currently `dgaf` can:

```bash
dgaf run build develop install test docs blog lint
```

* build and install python packages
* test packages
* build documentation
* format a blog
* lint the project

## why `dgaf`?

`dgaf` is designed from experience with configuring python projects from nascent content. there is a lot of work to do around the content. each time we want to blog, we spend 20% writing and 80% building the damn thing. `dgaf` wants you to focus on content, by configuring your projects based on its contents.

`dgaf` is at its best with new content, gist sized content, and it is good at automatically building binders.

## use cases

### I have one ~~notebook, script, markdown file~~ document

`dgaf` turns these document forms into a python package, a test object, and documentation. A common way to share this document would be to share it as a gist. `dgaf` does this with the `dgaf gist` subcommand.

```bash
dgaf gist push # this only work with the gh cli
```

the single document is uploaded with a `"postBuild"` file that runs `dgaf` on the respective binder. the resulting binder represents a full development environment for the content.

### I have a bunch of documents

`dgaf` uses the relationships between files and directories to configure the development tools.

documents in a folder ... uses the directory as the name
documents in a folder ... exclude some common name conventions like `"github" and "docs"`

top-level documents ...
top-level documents ... require a name

folders in the top-level... require an explicit name

### smoke testing

a smoke test is a top-level context independent test. it tests from source

## development

`dgaf` uses `nox`

```bash
nox -s develop
```

## currently some of the configurations are incomplete.

* https://mozillascience.github.io/working-open-workshop/contributing/
* https://gist.github.com/bollwyvl/f6aac8d4e68e5594fad2ae7a3cacc74b
* https://gist.github.com/tonyfast/f74eb42f2a998d8e428a752ceb0cb1d1
* https://github.com/carlosperate/awesome-pyproject
* https://twitter.com/SourabhSKatoch/status/1330068683222183936?s=20
* https://setuptools.readthedocs.io/en/latest/userguide/declarative_config.html
* https://pre-commit.com/hooks.html
* https://github.com/nbQA-dev/nbQA
* https://docs.python.org/3/distutils/configfile.html
* https://pyscaffold.org/en/latest/features.html

should we pre install a bunch of different pytest opinions?

[github actions]: #
https://github.com/David-OConnor/pyflow
