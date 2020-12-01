import qpub
import pathlib
import functools
import dataclasses
import doit
import typing

Path = type(pathlib.Path())

compat = {"yml": "yaml", "cfg": "ini"}
pkg2pip = dict(git="GitPython", dotenv="python-dotenv")


def make_conda_pip_envs():
    import json
    import doit

    file = qpub.File("environment.yml") or qpub.File("environment.yaml")
    file or make_prior_env()
    reqs = qpub.File("requirements.txt")
    reqs.touch()
    env = file.load()
    if not env.get("dependencies", []):
        return
    cmd = doit.tools.CmdAction(
        " ".join(
            ["conda install --dry-run --json"]
            + [x for x in env.get("dependencies", []) if isinstance(x, str)]
        )
    )
    cmd.execute()
    result = json.loads(cmd.out)
    if "success" in result:
        ...
    if "error" in result:
        if result.get("packages"):
            reqs = qpub.File("requirements.txt")
            reqs.write_text(
                "\n".join(
                    set(filter(str.strip, reqs.read_text().splitlines())).union(
                        result["packages"]
                    )
                )
            )

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

            file.dump(env)


def depfinder(*files) -> set:
    """Find the dependencies for all of the content."""
    import yaml

    if not hasattr(yaml, "CSafeLoader"):
        yaml.CSafeLoader = yaml.SafeLoader

    import depfinder

    object = {}
    deps = set()
    for file in files:
        deps = deps.union(file.imports())
    deps.discard("qpub")
    return {x for x in deps if x not in "python"}


def is_site_package(name):
    path = __import__("importlib").find_loader(name).path

    return any(path.startswith(x) for x in __import__("site").getsitepackages())


def is_installed(object: str) -> bool:
    """is a specific dependency installed."""
    return bool(__import__("importlib").util.find_spec(object))


def ensure_conda() -> bool:
    import contextlib, io

    ensureconda = __import__("ensureconda.cli")

    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(
        io.StringIO()
    ):
        try:
            ensureconda.cli.ensureconda_cli.main([])
        except SystemExit as e:
            if e.args[0]:
                return False
            return True


def task(name, input, output, actions, **kwargs):
    """serialize a doit task convention"""
    if input == ...:
        input = []
    if not isinstance(input, list):
        input = [input]
    if output == ...:
        output = []
    if not isinstance(output, list):
        output = [output]
    if actions == ...:
        actions = []
    if not isinstance(actions, list):
        actions = [actions]

    kwargs["file_dep"] = kwargs.get("file_dep", [])
    kwargs["uptodate"] = kwargs.get("uptodate", [])
    kwargs["targets"] = kwargs.get("targets", []) + output
    for i in input:
        if isinstance(i, (dict, str)):
            kwargs["uptodate"] = kwargs["uptodate"] + [doit.tools.config_changed(i)]
        elif isinstance(i, pathlib.Path):
            kwargs["file_dep"] = kwargs["file_dep"] + [i]

        elif isinstance(i, bool):
            kwargs["uptodate"] = kwargs["uptodate"] + [i]
    return dict(name=name, actions=actions, **kwargs)


def rough_source(nb):
    """extract a rough version of the source in notebook to infer files from"""
    import textwrap, json

    if isinstance(nb, str):
        nb = json.loads(nb)

    return "\n".join(
        textwrap.dedent("".join(x["source"]))
        for x in nb.get("cells", [])
        if x["cell_type"] == "code"
    )


async def infer(file):
    """infer imports from different kinds of files."""
    import aiofiles, depfinder, json

    async with aiofiles.open(file, "r") as f:
        if file.suffix not in {".py", ".ipynb", ".md", ".rst"}:
            return file, {}
        source = await f.read()
        if file.suffix == ".ipynb":
            source = rough_source(file.read_text())
        try:
            return file, depfinder.main.get_imported_libs(source).describe()
        except SyntaxError:
            return file, {}


async def infer_files(files):
    return dict(
        await __import__("asyncio").gather(
            *(infer(file) for file in map(pathlib.Path, files))
        )
    )


def gather_imports(files: typing.List[Path]) -> typing.List[dict]:
    """"""
    import asyncio, sys

    if "depfinder" not in sys.modules:

        dir = Path(__import__("appdirs").user_data_dir("qpub"))
        __import__("requests_cache").install_cache(str(dir / "qpub"))
        dir.mkdir(parents=True, exist_ok=True)
        import depfinder

        __import__("requests_cache").uninstall_cache()

    return asyncio.run(infer_files(files))


def _merge_shallow(a: dict, b: dict, *c: dict) -> dict:
    """merge the results of dictionaries."""
    a = a or {}
    b = functools.reduce(_merge_shallow, (b, *c)) if c else b
    for k, v in b.items():
        if k not in a:
            a[k] = a.get(k, [])
        for v in v:
            a[k] += [] if v in a[k] else [v]
    return a


def merged_imports(files: typing.List[Path]) -> dict:
    results = _merge_shallow(*gather_imports(files).values())
    return results.get("required", []) + results.get("questionable", [])


IMPORT_TO_PIP = None
PIP_TO_CONDA = None


def import_to_pip(list):
    import depfinder

    global IMPORT_TO_PIP
    if not IMPORT_TO_PIP:
        IMPORT_TO_PIP = {
            x["import_name"]: x["pypi_name"] for x in depfinder.utils.mapping_list
        }
    return [IMPORT_TO_PIP.get(x, x) for x in list]


def pypi_to_conda(list):
    import depfinder

    global PIP_TO_CONDA
    if not PIP_TO_CONDA:
        PIP_TO_CONDA = {
            x["import_name"]: x["cond`a_name"] for x in depfinder.utils.mapping_list
        }
    return [PIP_TO_CONDA.get(x, x) for x in list]


def valid_import(object: typing.Union[str, typing.Iterable]) -> bool:
    """determine if an object can be joined into a valid import statement."""
    if isinstance(object, Path):
        object = ".".join(object.parts)
    try:
        return bool(__import__("ast").parse(object))
    except SyntaxError:
        return False
