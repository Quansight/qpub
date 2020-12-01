import qpub
import pathlib
import functools
import dataclasses
import doit

Path = type(pathlib.Path())

compat = {"yml": "yaml", "cfg": "ini"}
pkg2pip = dict(git="GitPython", dotenv="python-dotenv")


def squash_depfinder(object):
    import depfinder.inspection

    if isinstance(object, tuple):
        object = object[-1]
    if isinstance(object, depfinder.inspection.ImportFinder):
        object = object.describe()
    return set(
        map(
            lambda x: pkg2pip.get(x, x),
            set(object.get("required", set())).union(object.get("questionable", set())),
        )
    )


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
    import contextlib, io, ensureconda.cli

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


def install_task(object, **kwargs):
    return task(
        f"install-{object}",
        qpub.util.is_installed(object),
        ...,
        f"python -m pip install {object}",
        **kwargs,
    )


def get_name(self):
    directories = {x.parts[0] for x in self.DIRECTORIES}
    if len(directories) == 1:
        return next(iter(directories))


def to_metadata_options(self):
    import setuptools

    UNKNOWN = "UNKNOWN"
    data = dict()
    object = data["metadata"] = dict()
    if self.distribution.get_name() == UNKNOWN:
        object["name"] = get_name(self)
    if self.distribution.get_version() == "0.0.0":
        object["version"] = __import__("datetime").date.today().strftime("%Y.%m.%d")
    if self.distribution.get_url() == UNKNOWN:
        object["url"] = self.REPO.remote("origin").url
        if object["url"].endswith(".git"):
            object["url"] = object["url"][: -len(".git")]

    if self.distribution.get_download_url() == UNKNOWN:
        # populate this for a release
        pass

    if self.distribution.get_author() == UNKNOWN:
        object["author"] = self.REPO.commit().author.name

    if self.distribution.get_author_email() == UNKNOWN:
        object["author_email"] = self.REPO.commit().author.email

    if self.distribution.get_maintainer() == UNKNOWN:
        pass

    if self.distribution.get_maintainer_email() == UNKNOWN:
        pass

    if not self.distribution.get_classifiers():
        # import trove_classifiers
        # https://github.com/pypa/trove-classifiers/
        pass

    if self.distribution.get_license() == UNKNOWN:
        # There has to be a service for these.
        pass

    if self.distribution.get_description() == UNKNOWN:
        object["description"] = ""

    if self.distribution.get_long_description() == UNKNOWN:
        # metadata['long_description_content_type']
        object[
            "long_description"
        ] = f"""file: {qpub.base.File("readme.md") or qpub.base.File("README.md")}"""

    if not self.distribution.get_keywords():
        pass

    if self.distribution.get_platforms() == [UNKNOWN]:
        pass

    if not self.distribution.get_provides():
        # https://www.python.org/dev/peps/pep-0314/
        pass

    if not self.distribution.get_requires():
        # cant have versions?
        pass

    if not self.distribution.get_obsoletes():
        pass

    object = data["options"] = dict()
    if self.distribution.zip_safe is None:
        object["zip_safe"] = False

    if not self.distribution.setup_requires:
        pass
    if not self.distribution.install_requires:
        object["install_requires"] = (
            qpub.base.REQUIREMENTS.read_text().splitlines()
            if qpub.base.REQUIREMENTS
            else []
        )
    if not self.distribution.extras_require:
        data["options.extras_require"] = dict(test=[], docs=[])
        pass

    if not self.distribution.python_requires:
        pass
    if not self.distribution.entry_points:
        data["options.entry_points"] = {}

    if self.distribution.scripts is None:
        pass

    if self.distribution.eager_resources is None:
        pass

    if not self.distribution.dependency_links:
        pass
    if not self.distribution.tests_require:
        pass
    if self.distribution.include_package_data is None:
        object["include_package_data"] = True

    if self.distribution.packages is None:
        object["packages"] = self.packages

    if not self.distribution.package_dir:
        if qpub.base.SRC.exists():
            object["package_dir"] = ["=src"]
        pass

    if not self.distribution.package_data:
        pass

    if self.distribution.exclude_package_data is None:
        pass

    if self.distribution.namespace_packages is None:
        pass

    if not self.distribution.py_modules:
        pass

    if not self.distribution.data_files:
        pass

    return data


async def infer(file):
    """infer imports from different kinds of files."""
    import aiofiles, depfinder, nbconvert, nbformat

    async with aiofiles.open(file, "r") as f:
        if file.suffix not in {".py", ".ipynb", ".md", ".rst"}:
            return file, {}
        source = await f.read()
        if file.suffix == ".ipynb":
            source = nbconvert.PythonExporter().from_notebook_node(
                nbformat.reads(source, 4)
            )[0]
        try:
            return file, depfinder.main.get_imported_libs(source).describe()
        except SyntaxError:
            return file, {}


async def infer_files(files):
    import asyncio

    return dict(
        await asyncio.gather(*(infer(file) for file in map(pathlib.Path, files)))
    )


def gather_imports(files):
    import asyncio

    return asyncio.run(infer_files(files))


def _merge_shallow(a, b, *c):
    """merge the results of dictionaries."""
    a = a or {}
    b = functools.reduce(_merge_shallow, (b, *c)) if c else b
    for k, v in b.items():
        if k not in a:
            a[k] = a.get(k, [])
        for v in v:
            a[k] += [] if v in a[k] else [v]
    return a


def merged_imports(files):
    results = _merge_shallow(*gather_imports(files).values())
    return results.get("required", []) + results.get("questionable", [])
