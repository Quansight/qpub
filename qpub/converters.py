"""converters.py"""
import qpub
from qpub import File
from qpub.base import *
import doit


def to_deps(FILES):
    dependencies = set(qpub.util.depfinder(*FILES))

    for x in "python".split():
        x in dependencies and dependencies.remove(x)

    return list(imports_to_pypi(*dependencies))


def setup_cfg_to_environment_yml():
    data = SETUPCFG.load()
    current = ENVIRONMENT.load()
    if "dependencies" not in current:
        current["dependencies"] = []
    current["dependencies"] += [
        x
        for x in pypi_to_conda(*data["options"]["install_requires"].splitlines())
        if x not in current["dependencies"]
    ]
    ENVIRONMENT.dump(current)


def pypi_to_conda(*object):
    import depfinder.main

    import_to_conda = {
        k: v
        for dict in [
            {x["pypi_name"]: x["conda_name"] for x in depfinder.utils.mapping_list},
            *depfinder.utils.pkg_data.values(),
        ]
        for k, v in dict.items()
    }
    yield from (import_to_conda.get(x, x) for x in object)


def imports_to_pypi(*object):
    import depfinder.main

    import_to_pypi = {
        k: v
        for dict in [
            {x["import_name"]: x["pypi_name"] for x in depfinder.utils.mapping_list},
            *depfinder.utils.pkg_data.values(),
        ]
        for k, v in dict.items()
    }
    yield from (import_to_pypi.get(x, x) for x in object)


def pip_to_conda(write=True, to=None):
    to = to or ENVIRONMENT
    data = dict(dependencies=list(REQUIREMENTS.load()))
    cmd = doit.tools.CmdAction(
        " ".join(["conda install --dry-run --json"] + REQUIREMENTS.load())
    )
    cmd.execute()
    result = qpub.util.Dict(__import__("json").loads(cmd.out))

    if "error" in result:
        if result["/packages"]:
            env = to.load()
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

            env["dependencies"] = list(
                set(x for x in env["dependencies"] if isinstance(x, str))
            ) + [pip]

            ENVIRONMENT.dump(env)
    if write:
        to.dump(to.load(), **data)
    return data


def to_python_modules():
    for directory in DIRECTORIES:
        if str(directory).startswith((".", "_")):
            continue
        init = directory / "__init__.py"
        if not init.exists():
            init.touch()


def to_dev_requirements(*extras):
    tool = PYPROJECT.load()["/tool"]
    for x in "black isort flakehell pytest".split():
        extras += (x,)
    return extras
