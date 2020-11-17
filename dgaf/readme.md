# deathbeds generalized automation framework

`dgaf` expands compact content into development, documentation, and testing environments.

    import git, typing, dgaf, doit, shutil, typer, sys, os
    from dgaf import File, merge
    from doit.tools import LongRunning
    from dgaf.files import *
    $RAISE_SUBPROC_ERROR = True

all of the CLI commands need to be defined in `__all__`.

    __all__ = "infer preinstall develop install binder conda test docs blog".split()

## infer the environment

    def infer():

infer the dependencies from the existings repository contents. 

        #

inference looks through common python and conda files along with using depfinder to infer the contents of notebooks and scripts. the contents are written to `REQUIREMENTS`.

        REQUIREMENTS.dump(dgaf.converters.to_deps())

`PYPROJECT and SETUP` files are then generated from the requirements.

        dgaf.converters.to_flit(), dgaf.converters.flit_to_setup()

    def conda():

when `CONDA` is available, `ENVIRONMENT` files created. for example, we'll prefer `CONDA` when creating binders.

        dgaf.converters.to_conda()

    def preinstall():

install dependencies from `CONDA, REQUIREMENTS` before building the package.

        if CONDA and ENVIRONMENT:
            LongRunning(F"conda env update {ENVIRONMENT}")
        if REQUIREMENTS:
            LongRunning(F"pip install {REQUIREMENTS}")

        
    def develop():

install development versions of the local packages.

        if SETUP:
            return $[pip install -e.]

        data = PYPROJECT.load()
        if data['/build-system/build-backend']:
            if data['/build-system/build-backend'].startswith("flit_core"):
                $[flit install -s]
        

    def install():

install built versions of the local packages.

        $[pip install .]

    def build():

build a wheel the python module

        if PYPROJECT:
            data = PYPROJECT.load()
            if data['/build-system/build-backend'].startswith("flit_core"):
                return ![flit build]
            if data['/build-system/build-backend'].startswith("poetry"):
                return ![poetry build]
        if SETUP:
            return ![python setup.py sdist bdist_wheel]


    def binder():

use this command to build binder environments.

        return [infer(), conda(), preinstall(), develop(), build()]

    def docs():

build documentation with [jupyter book].

        File('docs').mkdir(parents=True, exist_ok=True)
        ![jb toc .]
        CONFIG = File("_config.yml")
        CONFIG.dump(
            CONFIG.load(), dgaf.template._config,
            repository=dict(url=REPO.remote("origin").url[:-len(".git")])
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

    [dgaf.app.command()(x) for x in map(locals().get, __all__)]

[`flit`]: #
[`poetry`]: #
[jupyter book]: #