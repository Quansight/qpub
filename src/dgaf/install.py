"""install packages into conda and python environments."""

from .__init__ import *
import shutil
import doit


def task_pip():
    return Task(
        file_dep=[REQUIREMENTS_TXT],
        actions=[f"pip install -r{REQUIREMENTS_TXT} --no-deps"],
    )


def task_conda():
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


def task_build():
    def build(develop, pip)::
        if develop:
            return
        if pip:
            needs("pep517")
            assert not doit.tools.CmdAction("pip install . --no-deps").execute()
        elif PYPROJECT_TOML.exists():
            backend = build_backend()
            if backend == "flit_core":
                needs("flit")
                assert not doit.tools.LongRunning("flit install").execute()
            elif backend == "poetry":
                needs("poetry")
                assert not doit.tools.LongRunning("poetry install").execute()
            else:
                assert not doit.tools.LongRunning(
                    "pip install . --no-deps"
                ).execute()

    return Task(
        file_dep=[PYPROJECT_TOML],
        actions=[build],
        params=[Param("develop", True, type=bool), Param("pip", False, type=bool)],
    )


def task_install():
    def install(develop, pip):
        if develop:
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
                    assert not doit.tools.LongRunning(
                        "pip install -e. --no-deps"
                    ).execute()
        else:
            if pip:
                assert not doit.tools.CmdAction("pip install . --no-deps").execute()
            elif PYPROJECT_TOML.exists():
                backend = build_backend()
                if backend == "flit_core":
                    needs("flit")
                    assert not doit.tools.LongRunning("flit install").execute()
                elif backend == "poetry":
                    needs("poetry")
                    assert not doit.tools.LongRunning("poetry install").execute()
                else:
                    assert not doit.tools.LongRunning(
                        "pip install . --no-deps"
                    ).execute()

    return Task(
        file_dep=[PYPROJECT_TOML],
        actions=[install],
        task_dep=["build"],
        params=[Param("develop", True, type=bool), Param("pip", False, type=bool)],
    )


conda, mamba = bool(shutil.which("conda")), bool(shutil.which("mamba"))

if __name__ == "__main__":
    if ENVIRONMENT_YAML.exists():
        DOIT_CONFIG["default_tasks"] += ["conda"]

    if REQUIREMENTS_TXT.exists():
        DOIT_CONFIG["default_tasks"] += ["pip"]

    DOIT_CONFIG["default_tasks"] += ["install"]

    main(globals())