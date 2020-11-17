# deathbeds generalized automation framework

`dgaf` expands compact content into development, documentation, and testing environments.

    import git, typing, dgaf, doit, shutil, typer, sys, os
    from dgaf import File, merge, files as f
    from doit.tools import LongRunning
    from dgaf.files import *

all of the CLI commands need to be defined in `__all__`.

    __all__ = "infer setup develop install binder conda test docs blog".split()

## infer the environment

    def infer():

infer the dependencies from the existings repository contents. 

a common need in reproducible environments is to define environment files for pip in a `REQUIREMENTS` or python configuration file; in scientific computing worlds `CONDA` requirements become important.

the `infer` method uses existing configuration files like `PYPROJECT, SETUPCFG or SETUPPY`. `dgaf.converters.to_dep` walks the `git` content then uses notebooks, python scripts, and markdown to infer environment parameters.

        deps = dgaf.converters.to_deps()

        if f.REQUIREMENTS not in f.INCLUDE:

write then `REQUIREMENTS` file from the inferred dependencies

            f.REQUIREMENTS.dump(deps)

        if f.PYPROJECT not in f.INCLUDE:

write the `"/tool/flit/metadata/"` to the `PYPROJECT` file

            dgaf.converters.to_flit(deps)

        if f.SETUPPY not in f.INCLUDE:

create a `SETUPPY` file from the `PYPROJECT` configuration

            dgaf.converters.flit_to_setup(deps)

        if f.CONDA and f.ENVIRONMENT not in f.INCLUDE:

expand the requirements into things `CONDA` can solve, and things that we need to defer `REQUIREMENTS` for

            conda(deps)

    def conda(deps=None):

infer `CONDA` environments from different configuration files.

        deps = deps or REQUIREMENTS and REQUIREMENTS.load()
        dgaf.converters.to_conda(deps)

    def setup():

setup the environment with `CONDA` or `pip`

        if f.CONDA and f.ENVIRONMENT:

if conda is available and an `ENVIRONMENT` is available then we update the environment; this is practical on jupyterhub and binder.

            ![conda env update @(ENVIRONMENT)]

        if f.REQUIREMENTS:

we fallback to install the `REQUIREMENTS` with `pip`. 

            ![pip install -r @(REQUIREMENTS)]

these patterns are practical for developing in `CONDA` and testing in Github Actions.

        
    def develop():

install development versions of the local packages.

        if f.SETUPPY:

the `SETUPPY` is still the best way to install development versions.

            return $[pip install -e. ]

        data = f.PYPROJECT.load()
        if data['/build-system/build-backend']:

if `SETUPPY` is ignored then we use flit if that backend is specified

            if data['/build-system/build-backend'].startswith("flit_core"):
                $[flit install -s]

> i haven't figured out how `poetry` works in develop mode.
        

    def install():

install built versions of the local packages  with `pip`

        $[pip install .]

    def build():

build a wheel the python module

        if f.PYPROJECT:

use `flit or poetry` builds if they are the specified build backend.

            data = f.PYPROJECT.load()
            if data['/build-system/build-backend'].startswith("flit_core"):
                return ![flit build]
            if data['/build-system/build-backend'].startswith("poetry"):
                return ![poetry build]

        if f.SETUPPY:

use `SETUPPY` as a last resort

            return ![python setup.py sdist bdist_wheel]


    def binder():

use this command to build binder environments.

        return [infer(), setup(), develop(), build()]

    def docs():

build documentation with [jupyter book].

        File('docs').mkdir(parents=True, exist_ok=True)
        ![jb toc .]
        f.CONFIG = File("_config.yml")
        f.CONFIG.dump(
            f.CONFIG.load(), dgaf.template._config,
            repository=dict(url=f.REPO.remote("origin").url[:-len(".git")])
        )
        ![jb build .]
        if not File("html").exists():
            File("html").symlink_to(File("_build/html"), True)


    def blog():
        
build a blog with nikola

        # make decisions backed on content
        return [
            $[nikola init],
            $[jupyter nbconvert --to dgaf.exporters.Nikola **/*.ipynb]
        ]

    def test():

test the project

        if os.getenv("CI"):

install a package that interfaces pytest with github actions annotations.

              $[python -m pip install pytest-github-actions-annotate-failures]

        return $[pytest]
        

append all of the methods to the `dgaf` cli.

## `dgaf` application

add commands to the CLI based on the contents of `__all__`

    [dgaf.app.command()(x) for x in map(locals().get, __all__)]

set `xonsh` to raise errors when subprocess fail.

    $RAISE_SUBPROC_ERROR = True


[`flit`]: #
[`poetry`]: #
[jupyter book]: #