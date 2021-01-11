"""install packages into conda and python environments."""

from .__init__ import *
import shutil
import doit

_DEVELOP = Param(
    "develop",
    True,
    type=bool,
    help="use development tools to build the project.",
)
_PIP = Param(
    "pip",
    False,
    type=bool,
    help="build with generic standard python packaging tools.",
)


def task_pip():
    """install pip requirements"""
    return Task(
        file_dep=[REQUIREMENTS_TXT],
        actions=[f"pip install -r{REQUIREMENTS_TXT} --no-deps"],
    )


def task_conda():
    """install conda requirements"""

    def conda(mamba):
        backend = mamba and "mamba" or "conda"
        # assert not doit.tools.LongRunning(f"{backend} install").execute()

    return Task(
        file_dep=[ENVIRONMENT_YAML],
        params=[Param("mamba", mamba)],
    )


def build_backend():
    return (
        PYPROJECT_TOML.load()
        .get(BUILDSYSTEM, {})
        .get("build-backend", None)
        .partition(".")[0]
    )


def to_whl(dir, name, version):
    """generate the name of the target wheel."""
    return dir / DIST / f"{name}-{version}-py3-none-any.whl"


def to_sdist(dir, name, version):
    """generate the name of the target sdist."""
    return dir / DIST / f"{name}-{version}.tar.gz"


def task_build():
    """build the python project."""

    def build(develop, pip):
        if pip:
            needs("pep517")
            assert not doit.tools.CmdAction("python -m pep517.build .").execute()
        elif PYPROJECT_TOML.exists():
            backend = build_backend()
            print(backend)
            if backend == "flit_core":
                needs("flit")
                assert not doit.tools.CmdAction("flit build").execute()
            elif backend == "poetry":
                needs("poetry")
                assert not doit.tools.CmdAction("poetry build").execute()
            else:
                needs("pep517")
                assert not doit.tools.CmdAction("python -m pep517.build .").execute()

    name, version = get_name(), get_version()
    return Task(
        file_dep=[PYPROJECT_TOML],
        actions=[build],
        targets=[to_whl(Path(), name, version), to_sdist(Path(), name, version)],
        params=[_DEVELOP, _PIP],
    )


def task_install():
    """install the packages into the sys.packages"""

    def install(pip):
        if pip:
            name = get_name()

            assert not doit.tools.CmdAction(
                f"python -m pip install --find-links=dist --no-index --ignore-installed --no-deps {name}"
            ).execute()
        elif PYPROJECT_TOML.exists():
            backend = build_backend()
            if backend == "flit_core":
                needs("flit")
                assert not doit.tools.LongRunning("flit install").execute()
            elif backend == "poetry":
                needs("poetry")
                assert not doit.tools.LongRunning("poetry install").execute()
            else:
                assert not doit.tools.LongRunning("pip install . --no-deps").execute()

    name, version = get_name(), get_version()
    return Task(
        file_dep=[
            PYPROJECT_TOML,
            to_whl(Path(), name, version),
            to_sdist(Path(), name, version),
        ],
        actions=[install],
        task_dep=["build"],
        params=[_DEVELOP, _PIP],
    )


def task_develop():
    """install the project in development mode."""

    def develop(pip):
        if pip:
            assert not doit.tools.CmdAction("pip install -e.")
        elif PYPROJECT_TOML.exists():
            backend = build_backend()
            if backend == "flit_core":
                needs("flit")
                assert not doit.tools.LongRunning("flit install -s").execute()
            elif backend == "poetry":
                needs("poetry")
                assert not doit.tools.LongRunning("poetry install").execute()
            else:
                assert not doit.tools.LongRunning("pip install -e. --no-deps").execute()

    return Task(
        file_dep=[PYPROJECT_TOML],
        actions=[develop],
        params=[_DEVELOP, _PIP],
    )


conda, mamba = bool(shutil.which("conda")), bool(shutil.which("mamba"))

DOIT_CONFIG["default_tasks"] += ["develop"]

if __name__ == "__main__":

    main(globals())