"""the dgaf api. an opinionated cli of cli's.
"""

import git
import flit
import typing
import anyconfig
import dgaf.template
import pathlib
import dgaf
import doit
import shutil
import sys
from . import dodo
from dgaf import File
from doit.tools import LongRunning
import typer

# load in all the configuration details we can.

REPO = git.Repo()
PYPROJECT = dgaf.merge(dgaf.File("pyproject.toml").load(),
                       dgaf.template.pyproject)

FLIT = PYPROJECT["tool"]["flit"]["metadata"]
if PYPROJECT.get("tool", {}).get("dgaf", {}).get("env", ""):
    ...

ENV = dgaf.File(".env").load()


exclude_globs = []
files = list(
    x for x in File().iterdir() if x not in exclude_globs
)


class Settings:

    """what is the form of the project.

    - repo with no folders?
    - repo with folders?
    - repo with submodules?
    - repo with external references
    - are there subpackages to install
    - what are the module names defined within?
    """

    # the settings logic is open to discussion.
    # names can be inferred from different conventions.
    conda_env = ENV["CONDA_DEFAULT_ENV"]
    conda_exe = ENV["CONDA_EXE"]
    doit_cfg = File(".doit.cfg").load()
    name = FLIT["module"]
    author = FLIT["author"] or REPO.commit().author
    # TODO: list whether a directory is checked into git
    deep = all(map(File.is_dir, files))
    flat = not deep  # True typically reflects a gist.
    # TODO: use GIT.submodules
    submodules = bool(File(".gitmodules"))
    name = FLIT["module"]
    locals().update(flit.common.get_info_from_module(flit.common.Module(name, File())))
    assert summary, version

    # we can learn from conf.py, pyproject.toml, setup.py, setup.cfg, environment.yml


def make_pyproject():
    author = REPO.commit().author
    FLIT["module"] = FLIT.get("module", "") or "readme"
    FLIT["author"] = FLIT.get("author", "") or author.name
    FLIT["author-email"] = FLIT.get("author", "") or author.email
    FLIT["homepage"] = "http://"
    # add requirements
    File("pyproject.toml").dump(PYPROJECT)


def pyproject(flit: bool = True, poetry: bool = True, setuptools: bool = False) -> File("pyproject.toml"):
    """Create a pyproject or setuptools configuration file. We need setuptools with multiple packages.
    everything is a package unless ignored"""
    if flit:
        return make_pyproject()
    if setuptools:
        # what conditions need to exist to get here.
        return
    return


def python():
    """walk through the directory and add init files and main files."""
    return


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


def calculate_deps(conda: bool = True, pip: bool = True) -> (
    File("environment.yml") or File("environment.yaml"),
    File("requirements.txt")
):
    """calculate dependencies for a project using depfinder."""
    if conda:
        dgaf.util.make_conda_pip_envs()
    return


def docs() -> []:
    """build the docs."""
    return [LongRunning("jb init && jb toc").execute(), LongRunning("jb build").execute()]


def blog(jb: bool = True) -> File("conf.py"):
    """configure a blog with nikola."""
    return [
        LongRunning("nikola init").execute(),
        LongRunning("jupyter nbconvert --to dgaf.exporters.Nikola **/*.ipynb"
                    ).execute()  # should add markup to rst and markdown.

    ]


def update(pip: bool = True,  conda: bool = True, mamba: bool = False,
           poetry: bool = False):
    """update the environment.
    what file can be produced here?"""
    if conda:
        file = dgaf.File("environment.yml") or dgaf.File("environment.yaml")
        if file:
            return LongRunning(F"conda env update --file {file}").execute()
    if pip:
        file = dgaf.File("requirements.txt")
        if file:
            return LongRunning(F"pip install -r {file}").execute()
    return


def build(flit: bool = True, setuptools: bool = True):
    if flit:
        return LongRunning("flit build").execute()


def jupyter():
    """setup the jupyter configuration and extensions."""
    return


def js():
    """install javascript environment and dependencies."""
    return


def grayskull() -> (File("build/*.tar.gz"), File("recipes/{{ package.name }}/meta.yaml")):
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
                "requires_dist": [FLIT["requires"]],
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


def postBuild(): (
    [calculate_deps, pyproject, build], ...


)

# doit.doit_cmd.DoitMain(doit.cmd_base.ModuleTaskLoader(
# vars(dodo))).run(sys.argv[1:])


app = typer.Typer()
[app.command()(x) for x in [make_pyproject, pyproject, python, test, lint,
                            calculate_deps, docs, blog, update, build, jupyter, js, grayskull]
 ]
