"""build and install packages into conda and python environments."""

import shutil
import sys

import doit

from .__init__ import (
    BUILDSYSTEM,
    DIST,
    DOIT_CONFIG,
    ENVIRONMENT_YAML,
    PYPROJECT_TOML,
    REQUIREMENTS_TXT,
    Param,
    Path,
    Task,
    get_name,
    get_version,
    main,
    needs,
)

_DEVELOP = Param(
    "develop", True, type=bool, help="use development tools to build the project."
)
_PIP = Param(
    "pip", False, type=bool, help="build with generic standard python packaging tools."
)
_MAMBA = Param("mamba", bool(shutil.which("mamba")))
_CHANNELS = Param("channel", ["-cconda-forge"], type=list, short="c")


def task_pip():
    """install pip requirements"""
    return Task(
        file_dep=[REQUIREMENTS_TXT],
        actions=[f"pip install -r{REQUIREMENTS_TXT} --no-deps"],
    )


def task_conda():
    """install conda requirements"""

    def conda(mamba, channel):
        backend = mamba and "mamba" or "conda"
        data = ENVIRONMENT_YAML.load()
        deps = data.get("dependencies", [])
        pip = []
        for dep in deps:
            if isinstance(dep, dict):
                pip.extend(dep.pop("pip", []))

        assert not doit.tools.LongRunning(
            f"""{backend} install {" ".join(deps)}"""
        ).execute(sys.stdout, sys.stderr)
        if pip:
            assert not doit.tools.LongRunning(
                f"""pip install {" ".join(pip)} --no-deps"""
            ).execute(sys.stdout, sys.stderr)

    return Task(
        actions=[conda], file_dep=[ENVIRONMENT_YAML], params=[_MAMBA, _CHANNELS]
    )


def task_build():
    """build the python project."""

    def build(develop, pip):
        if pip:
            needs("pep517")
            assert not doit.tools.CmdAction("python -m pep517.build .").execute(
                sys.stdout, sys.stderr
            )
        elif PYPROJECT_TOML.exists():
            backend = build_backend()
            print(backend)
            if backend == "flit_core":
                needs("flit")
                assert not doit.tools.CmdAction("flit build").execute(
                    sys.stdout, sys.stderr
                )
            elif backend == "poetry":
                needs("poetry")
                assert not doit.tools.CmdAction("poetry build").execute(
                    sys.stdout, sys.stderr
                )
            else:
                needs("pep517")
                assert not doit.tools.CmdAction("python -m pep517.build .").execute(
                    sys.stdout, sys.stderr
                )

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
            ).execute(sys.stdout, sys.stderr)
        elif PYPROJECT_TOML.exists():
            backend = build_backend()
            if backend == "flit_core":
                needs("flit")
                assert not doit.tools.LongRunning("flit install").execute(
                    sys.stdout, sys.stderr
                )
            elif backend == "poetry":
                needs("poetry")
                assert not doit.tools.LongRunning("poetry install").execute(
                    sys.stdout, sys.stderr
                )
            else:
                assert not doit.tools.LongRunning("pip install . --no-deps").execute(
                    sys.stdout, sys.stderr
                )

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
                assert not doit.tools.LongRunning("flit install -s").execute(
                    sys.stdout, sys.stderr
                )
            elif backend == "poetry":
                needs("poetry")
                assert not doit.tools.LongRunning("poetry install").execute(
                    sys.stdout, sys.stderr
                )
            else:
                assert not doit.tools.LongRunning("pip install -e. --no-deps").execute(
                    sys.stdout, sys.stderr
                )

    return Task(file_dep=[PYPROJECT_TOML], actions=[develop], params=[_DEVELOP, _PIP])


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


DOIT_CONFIG["default_tasks"] += ["develop"]

if __name__ == "__main__":

    main(globals())
