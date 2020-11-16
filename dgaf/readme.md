# deathbeds generalized automation framework

`dgaf` expands compact content into development, documentation, and testing environments.

    import git, typing, dgaf, doit, shutil, typer, sys
    from dgaf import File, merge
    from doit.tools import LongRunning
    from dgaf.files import *

    __all__ = "infer preinstall develop install postbuild conda docs blog".split()

## infer the environment

    def infer():

`infer` the dependencies from content and configs.

begin by using `depfinder` to discover the dependencies requested by different pieces of content
including notebooks and python scripts

        dependencies = dgaf.converters.to_deps()
        
        REQUIREMENTS.dump(dependencies)

        dgaf.converters.to_flit(), dgaf.converters.flit_to_setup()

    def conda():

export a conda environment

        dgaf.converters.to_conda()

    def preinstall():

install dependencies before building the package.

        if CONDA and ENVIRONMENT:
            LongRunning(F"conda env update {ENVIRONMENT}")
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

        if PYPROJECT:
            data = PYPROJECT.load()
            if data['/build-system/build-backend'].startswith("flit_core"):
                return LongRunning("flit build").execute()
            if data['/build-system/build-backend'].startswith("poetry"):
                return LongRunning("poetry build").execute()
        if SETUP:
            return LongRunning("python setup.py build")


    def postbuild():

`postbuild` is used to make binders.

        return [infer(), conda(), preinstall(), develop(), build()]

    def docs():

build documentation with jupyter book.

        File('docs').mkdir(parents=True, exist_ok=True)
        LongRunning("jb toc . ").execute()
        CONFIG = File("_config.yml")
        CONFIG.dump(
            CONFIG.load(), dgaf.template._config,
            repository=dict(url=REPO.remote("origin").url[:-len(".git")])
        )
        LongRunning("jb build .").execute()
        if not File("html").exists():
            File("html").symlink_to(File("_build/html"), True)


    def blog(jb: bool = True) -> File("conf.py"):
        
build a blog with nikola

        return [
            LongRunning("nikola init").execute(),
            LongRunning("jupyter nbconvert --to dgaf.exporters.Nikola **/*.ipynb"
                        ).execute()  # should add markup to rst and markdown.

        ]

    def test():
        """test the project."""
        return LongRunning("pytest").execute()
        return LongRunning("tox").execute()


    [dgaf.app.command()(x) for x in map(locals().get, __all__)]

[`flit`]: #
[`poetry`]: #