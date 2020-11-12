import dgaf.template
import doit
import anyconfig
import pathlib
import typing

PYPROJECT = dgaf.merge(dgaf.File("pyproject.toml").load(),
                       dgaf.template.pyproject)

if PYPROJECT.get("tools", {}).get("dgaf", {}).get("env", ""):
    ...

ENV = dgaf.File(".env").load()


def split_envs():
    import json
    file = dgaf.File("environment.yml") or dgaf.File("environment.yaml")
    reqs = dgaf.File("requirements.txt")
    reqs.touch()
    env = file.load()
    if not env.get("dependencies", []):
        return
    cmd = doit.tools.CmdAction(
        " ".join(["conda install --dry-run --json"]+[
            x for x in env.get("dependencies", []) if isinstance(x, str)]))
    cmd.execute()
    result = json.loads(cmd.out)
    if "success" in result:
        ...
    if "error" in result:
        if result.get("packages"):
            reqs = dgaf.File("requirements.txt")
            reqs.write_text("\n".join(set(filter(str.strip, reqs.read_text().splitlines())).union(
                result['packages'])))

            env["dependencies"] = [
                x for x in env["dependencies"] if x not in result["packages"]
            ]
            for dep in env["dependencies"]:
                if isinstance(dep, dict) and "pip" in dep:
                    pip = dep
            else:
                pip = dict(pip=[])
                env["dependencies"].append(pip)
            pip["pip"] = list(set(pip["pip"]).union(result["packages"]))

            if "pip" not in env["dependencies"]:
                env["dependencies"] += ["pip"]

            env["dependencies"] = list(set(x for x in env["dependencies"]
                                           if isinstance(x, str))) + [pip]

            file.dump(env)


def task_local_dev_install():
    """use flit install a development version of the code."""
    return dict(actions=[
        "flit install -s"
    ], file_dep=["pyproject.toml"])


def make_pyproject():
    import git
    author = git.Repo().commit().author

    metadata = PYPROJECT.get("tool", {}).get("flit", {}).get("metadata", {})
    metadata["module"] = metadata.get("module", "") or "readme"
    metadata["author"] = metadata.get("author", "") or author.name
    metadata["author-email"] = metadata.get("author", "") or author.email
    metadata["homepage"] = "http://"
    # add requirements
    dgaf.File("pyproject.toml").dump(PYPROJECT)


def task_pyproject():
    return dict(actions=[
        make_pyproject,
    ], targets=["pyproject.toml"])


def depfinder() -> set:
    """Find the dependencies for all of the content."""
    import depfinder
    object = {}
    deps = set()
    for file in dgaf.File().iterdir():
        deps = deps.union(file.imports())
    deps.discard('dgaf')
    return deps


def make_env():
    """create and write conda environment file."""
    dependencies = depfinder()
    channels = ['conda-forge']
    file = dgaf.File("environment.yml") or dgaf.File("environment.yaml")

    if any(x in dependencies for x in ("panel", "holoviews", "hvplot")):
        channels = ['pyviz'] + channels

    file.dump(
        dgaf.merge(file.load(), dict(name="notebook", channels=channels,
                                     dependencies=list(dependencies)))
    )


def task_populate():
    return dict(actions=[make_env, split_envs], targets=[
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
