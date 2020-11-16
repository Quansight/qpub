# deathbeds generalized automation framework

`dgaf` expands compact content into development, documentation, and testing environments.

    import git, typing, dgaf, doit, shutil, typer, sys
    from dgaf import File, merge
    from doit.tools import LongRunning
    from dgaf.files import *

    __all__ = "infer preinstall develop install".split()

## infer the environment

    def infer():

`infer` the dependencies from existing configuration files and content.

begin by using `depfinder` to discover the dependencies requested by different pieces of content
including notebooks and python scripts

        # TODO: discover markdown scripts.


        # merge the projects
        pyproject = PYPROJECT.load()
        dependencies = set(
            dgaf.util.depfinder(*FILES)
        ).union(
            pyproject["/tool/flit/metadata/requires"] or []
        ).union(
            list(pyproject["/tool/poetry/dependencies"] or [])
        ).union(
            REQUIREMENTS.load()
        ) # .union(ENVIRONMENT.load())  # .union(SETUP.load())

        dependencies = list(dependencies)

        
        REQUIREMENTS.dump(dependencies)
        dgaf.converters.to_flit()
        # write conda stuff

    def preinstall():

install dependencies before building the package.

        if CONDA and ENVIRONMENT:
            LongRunning(F"conda update {ENVIRONMENT}")
        if REQUIREMENTS:
            LongRunning(F"pip install {REQUIREMENTS}")

        
    def develop():

install development versions of the local packages.

        if SETUP:
            LongRunning("pip install -e.").execute()
            return

        data = PYPROJECT.load()
        if data['/build-system/build-backend']:
            if data['/build-system/build-backend'].startswith("flit_core"):
                LongRunning("flit install -s").execute()
        

    def install():

install built versions of the local packages.

        LongRunning("pip install .").execute()

    def build():

build a wheel the python module

        if SETUP:
            return LongRunning("python setup.py build")

        data = PYPROJECT.load()
        if data['/build-system/build-backend'].startswith("flit_core"):
            return LongRunning("flit build").execute()
        if data['/build-system/build-backend'].startswith("poetry"):
            return LongRunning("poetry build").execute()


    def postbuild():

`postbuild` is used to make binders.

        return [infer(), install(), build(), docs()]

    def docs():
        """build the docs."""
        File('docs').mkdir(parents=True, exist_ok=True)
        LongRunning("jb toc . ").execute()
        CONFIG = File("_config.yml")
        CONFIG.dump(
            CONFIG.load(), dgaf.template._config,
            repository=dict(url=REPO.remote("origin").url[:-len(".git")])
        )
        LongRunning("jb build .").execute()
        File("html").symlink_to(File("_build/html"), True)


    def blog(jb: bool = True) -> File("conf.py"):
        """configure a blog with nikola."""
        return [
            LongRunning("nikola init").execute(),
            LongRunning("jupyter nbconvert --to dgaf.exporters.Nikola **/*.ipynb"
                        ).execute()  # should add markup to rst and markdown.

        ]        

    def test(unittest: bool = False, pytest: bool = True, tox: bool = False):
        """test the project."""
        if pytest:
            return LongRunning("pytest").execute()
        if tox:
            return LongRunning("tox").execute()
        return


    def lint(black: bool = True):
        """test the project."""
        return [
        ] + (
            [LongRunning("black .").execute()] if black else []
        )
        return



    def jupyter():
        """setup the jupyter configuration and extensions."""
        return


    def js():
        """install javascript environment and dependencies."""
        return

    [dgaf.app.command()(x) for x in map(locals().get, __all__)]

[`flit`]: #
[`poetry`]: #