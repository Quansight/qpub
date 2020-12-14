import dataclasses
import functools
import pathlib
import typing

Path = type(pathlib.Path())

compat = {"yml": "yaml", "cfg": "ini"}


def merge(a, b, *c):
    if c:
        b = functools.reduce(merge, (b,) + c)
    if hasattr(a, "items"):
        for k, v in a.items():
            if k in b:
                a[k] = merge(v, b[k])

        for k, v in b.items():
            if k not in a:
                a[k] = v

        return a
    if isinstance(a, str):
        return a

    if isinstance(a, (set, list, tuple)):
        return list(sorted(set(a).union(b)))


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
    import contextlib
    import io

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
    import doit

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
    import json
    import textwrap

    if isinstance(nb, str):
        nb = json.loads(nb)

    return "\n".join(
        textwrap.dedent("".join(x["source"]))
        for x in nb.get("cells", [])
        if x["cell_type"] == "code"
    )


async def infer(file):
    """infer imports from different kinds of files."""
    import json

    import aiofiles
    import depfinder

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
    import asyncio
    import sys
    import yaml

    if "depfinder" not in sys.modules:

        dir = Path(__import__("appdirs").user_data_dir("qpub"))
        __import__("requests_cache").install_cache(str(dir / "qpub"))
        dir.mkdir(parents=True, exist_ok=True)
        if not hasattr(yaml, "CSafeLoader"):
            yaml.CSafeLoader = yaml.SafeLoader
        import depfinder

        __import__("requests_cache").uninstall_cache()
    return dict(asyncio.run(infer_files(files)))


def _merge_shallow(a: dict, b: dict = None, *c: dict) -> dict:
    """merge the results of dictionaries."""
    a = a or {}
    if b is None:
        return a
    b = functools.reduce(_merge_shallow, (b, *c)) if c else b
    for k, v in b.items():
        if k not in a:
            a[k] = a.get(k, [])
        if isinstance(a[k], set):
            a[k] = list(a[k])
        for v in v:
            a[k] += [] if v in a[k] else [v]
    return a


def merged_imports(files: typing.List[Path]) -> dict:
    results = _merge_shallow(*gather_imports(files).values())
    return list(results.get("required", [])) + list(results.get("questionable", []))


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
            x["import_name"]: x["conda_name"] for x in depfinder.utils.mapping_list
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


def collect_test_items(path):
    """collect pytest items"""
    import _pytest.config

    config = _pytest.config._prepareconfig(
        ["--collect-only", f"--rootdir={path}", str(path)]
    )

    SESSION = None

    def _main(config, session):
        """Default command line protocol for initialization, session,
        running tests and reporting."""
        nonlocal SESSION
        from _pytest.main import ExitCode

        config.hook.pytest_collection(session=session)
        SESSION = session
        if session.testsfailed:
            return ExitCode.TESTS_FAILED
        elif session.testscollected == 0:
            return ExitCode.NO_TESTS_COLLECTED
        return None

    _pytest.main.wrap_session(config, _main)
    return SESSION.items


def collect_test_files(path=None):
    if path is None:
        path = Path()
    if not isinstance(path, Path):
        path = Path(path)
    return list({Path(x.keywords.parent.fspath) for x in collect_test_items(path)})


def nox_runner(module):
    """a wrapped nox runner specifically for qpub.

    it works off a module loaded into the namespace already
    rather than a static file.
    """
    import sys, nox

    argv = sys.argv
    sys.argv = ["tmp-program"]
    ns = nox._options.options.parse_args()
    sys.argv = argv
    # run the tasks ourselves to avoid switching directories

    nox.tasks.merge_noxfile_options(module, ns)
    manifest = nox.tasks.discover_manifest(
        module, ns
    )  # the manifest is a nox convention.
    nox.tasks.filter_manifest(manifest, ns)
    nox.tasks.verify_manifest_nonempty(manifest, ns)
    results = nox.tasks.run_manifest(
        manifest, ns
    )  # these are sessions results with their virtualenv instances.
    nox.tasks.print_summary(results, ns)
    nox.tasks.create_report(results, ns)
    return nox.tasks.final_reduce(results, ns)
