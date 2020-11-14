import dgaf.template
import doit
import anyconfig
import pathlib
import typing
import git

REPO = git.Repo()
PYPROJECT = dgaf.merge(dgaf.File("pyproject.toml").load(),
                       dgaf.template.pyproject)

print(PYPROJECT)

FLIT = PYPROJECT["tool"]["flit"]["metadata"]
if PYPROJECT.get("tool", {}).get("dgaf", {}).get("env", ""):
    ...

ENV = dgaf.File(".env").load()


class Settings:
    # the settings logic is open to discussion.
    # names can be inferred from different conventions.
    conda_env = ENV["CONDA_DEFAULT_ENV"]
    name = FLIT["module"]
    author = FLIT["author"] or REPO.commit().author

    # we can learn from conf.py, pyproject.toml, setup.py, setup.cfg, environment.yml


def task_local_dev_install():
    """use flit install a development version of the code."""
    if dgaf.File("setup.py"):
        return dict(actions=[
            "pip install -e."
        ], file_dep=["setup.py"])
    return dict(actions=[
        "flit install -s"
    ], file_dep=["pyproject.toml"])


def task_pyproject():
    return dict(actions=[
        dgaf.util.make_pyproject,
    ], targets=["pyproject.toml"])


def task_populate():
    return dict(actions=[dgaf.util.make_env, dgaf.util.split_envs], targets=[
        dgaf.File("environment.yml") or dgaf.File("environment.yaml")
    ])


def task_update_env():
    """If an environment file exists, install it."""
    file = dgaf.File("environment.yml") or dgaf.File("environment.yaml")
    alias = dgaf.Module("mamba") or "conda"
    return dict(actions=[
        F"{alias} env update --file {file}"
    ], file_dep=[file])


def task_setup():
    return dict(task_dep=[x.__name__[len('task_'):] for x in (
        task_populate, task_update_env, task_local_dev_install, task_build)], actions=[])


def task_build():
    return dict(actions=[
        F"flit build"
    ], file_dep=["pyproject.toml"], targets=["dist"])


def task_postBuild():
    return dict(task_dep=[x.__name__[len('task_'):] for x in (
        task_setup, task_docs)], actions=[])


def task_docs():
    def config():
        dgaf.File("_config.yml").dump(dgaf.template._config)
    # symlink the html after building it?
    return dict(
        actions=[
            config, "jb build --path-output docs ."
        ],
        file_dep=["_toc.yml", "_config.yml"],
        targets=["docs/index.html"]
    )


def task_test():
    return dict(
        actions=["pip install dgaf[test]", "pytest"]
    )


def task_nikola():
    """represent the content as a blog format."""
    # nikola init and add metadata
    return dict(actions=[
        "jupyter nbconvert --to dgaf.exporters.Nikola **/*.ipynb"
    ])


def task_toc():
    return dict(
        actions=["jb toc ."],
        targets=["_toc.yml"]
    )


def task_pdf():
    return dict(
        actions=["jb build --builder pdfhtml ."],
        file_dep=["_toc.yml", "_config.yml"]
    )


def task_contributing():
    return dict(actions=[])


def task_issue_template():
    return dict(actions=[])


def task_pull_request_template():
    return dict(actions=[])
