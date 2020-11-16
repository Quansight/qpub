the dgaf api. an opinionated cli of cli's.

    import git
    import typing
    import dgaf
    import doit
    import shutil
    import typer
    import sys
    # from . import dodo
    from dgaf import File, merge
    from doit.tools import LongRunning
    import typing

    from dgaf.files import *

## configure the `"pyproject.toml"`

    def configure():

Read in any existing `"pyproject.toml"` information and merge it with `dgaf`'s base templates.

find the name from the python files.
        
        dgaf.converters.to_pyproject()

## discover dependencies

discover dependencies and hard code them to the requirements.txt file.

    def discover():

discover the dependencies for project using `depfinder`
        
        REQUIREMENTS.dump(*dgaf.util.depfinder(*FILES).union(REQUIREMENTS.load()))

    def split_dependencies():

split conda dependencies from pip dependencies.

        if not CONDA: return
        dgaf.converters.pip_to_conda()

    def install():
        discover()
        configure()
        split_dependencies()
        data = PYPROJECT.load()
        if data['/build-system/build-backend']:
            if data['/build-system/build-backend'].startswith("flit_core"):
                LongRunning("flit install -s").execute()

    def build(flit: bool = True,poetry: bool = True, setuptools: bool = True):
        if poetry:
            return LongRunning("poetry build").execute()

        if poetry:
            return LongRunning("flit build").execute()

    def postbuild():

`postbuild` is used to make binders.

        return [install(), build(), docs()]

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


    def grayskull() -> [File("build/*.tar.gz"), File("recipes/{{ package.name }}/meta.yaml")]:
        """grayskull infers a conda build recipe from a pip compatible package/build.


        """
        File("recipes").mkdir(exist_ok=True)
        from grayskull.pypi import PyPi
        from grayskull.base.factory import GrayskullFactory

        class LocalPyPi(PyPi):

            # @staticmethod
            # def _download_sdist_pkg(sdist_url: str, dest: str):
            #     print("WOOO", sdist_url, dest)
            #     if not sdist_url.startswith("file://"):
            #         return OG["_download_sdist_pkg"](sdist_url, dest)
            #     tarball = File(
            #         "dist", f"{Settings.name}-{Settings.version}.tar.gz")
            #     shutil.copy(tarball, dest)

            def _get_sdist_metadata(self, sdist_url: str, name: str) -> dict:
                """Method responsible to return the sdist metadata which is basically
                the metadata present in setup.py and setup.cfg

                :param sdist_url: URL to the sdist package
                :param name: name of the package
                :return: sdist metadata
                """
                if not sdist_url.startswith("file://"):
                    return OG["_get_sdist_metadata"](sdist_url, name)

                from tempfile import mkdtemp, TemporaryDirectory
                import os

                tarball = File(
                    "dist", f"{Settings.name}-{Settings.version}.tar.gz")

                with TemporaryDirectory() as td:
                    tdp = File(td)
                    pkg_name = Settings.name
                    path_pkg = tdp / tarball.name
                    shutil.copy(tarball, path_pkg)
                    shutil.unpack_archive(tarball, tdp)
                    print("TD", td, )
                    import subprocess
                    print(subprocess.check_output(["ls", "-lathr", tdp]))
                    assert tdp.exists()
                    with PyPi._injection_distutils(str(td)) as metadata:
                        metadata["sdist_path"] = td
                        return metadata

            def _get_pypi_metadata(self, name, version: typing.Optional[str] = None) -> dict:
                """Method responsible to communicate with the pypi api endpoints and
                get the whole metadata available for the specified package and version.
                :param name: Package name
                :param version: Package version
                :return: Pypi metadata
                """
                if name != Settings.name:
                    return OG["_get_pypi_metadata"](name, version)

                tarball = File(
                    "dist", f"{Settings.name}-{Settings.version}.tar.gz")
                uri = tarball.resolve().as_uri()

                meta = {
                    "name": Settings.name,
                    "version": Settings.version,
                    "requires_dist": [],
                    "requires_python": [],
                    "summary": Settings.summary,
                    "project_url": FLIT["home-page"],
                    "doc_url": None,
                    "dev_url": None,
                    "url": FLIT["home-page"],
                    "license": FLIT["license"],
                    "source": {
                        "url": uri,
                        "sha256": "badbeef",
                    },
                    "sdist_url": uri,
                }
                print("META", meta)
                return meta

        OG = {
            "_download_sdist_pkg": PyPi._download_sdist_pkg,
            "_get_sdist_metadata": PyPi._get_sdist_metadata,
            "_get_pypi_metadata": PyPi._get_pypi_metadata
        }

        PyPi._download_sdist_pkg = LocalPyPi._download_sdist_pkg
        PyPi._get_sdist_metadata = LocalPyPi._get_sdist_metadata
        PyPi._get_pypi_metadata = LocalPyPi._get_pypi_metadata

        GrayskullFactory.REGISTERED_CLASS["localpypi"] = PyPi

        GrayskullFactory.create_recipe(
            "localpypi", Settings.name, Settings.version, is_strict_cf=True)


    def conda_build_test_install():
        """
            pushd {{ package.name }}
            {{ conda_build_exe }} {{ env.conda.channels }} . --output-folder ../dist/conda-bld --no-test \
                > ../build/conda-build.log
            popd

            {{ conda_build_exe }} build --test \
                dist/conda-bld/noarch/{{ package.name }}- \
                    {{ package.version }}.tar.bz2
                > build/conda-build-test.log

            {{ conda_exe }} install {{ env.conda.channels }} \
                dist/conda-bld/noarch/{{ package.name }}- \
                    {{ package.version }}.tar.bz2

            {{ conda_exe }} list | grep {{ package.name }}


        """

    app = typer.Typer()
    [app.command()(x) for x in [configure, test, lint,
                                docs, blog, build, jupyter, js, install, postbuild] #grayskull
    ]

[`flit`]: #
[`poetry`]: #