import dgaf
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


class File(Path):
    def __bool__(self):
        return self.is_file()

    def imports(self):
        import depfinder

        if self.suffix == ".py":
            deps = depfinder.parse_file(self)
        elif self.suffix == ".ipynb":
            deps = depfinder.notebook_path_to_dependencies(self)
        else:
            deps = {}
        return squash_depfinder(deps)

    def is_txt(self):
        return self.suffix == ".txt"

    def is_env(self):
        return self.suffix == ".env" or self.stem == ".env"

    def read_text_lines(self):
        return [
            line
            for line in map(str.strip, self.read_text().splitlines())
            if line and not line.startswith("# ")
        ]

    def is_gitignore(self):
        return (
            self.suffix == ".gitignore" if self.suffix else self == File(".gitignore")
        )

    def load(self):
        if self.is_gitignore():

            return self.read_text_lines()

        if self.is_txt():
            try:
                return self.read_text_lines()
            except FileNotFoundError:
                return []

        try:
            suffix = self.suffix.lstrip(".")
            suffix = compat.get(suffix, suffix)

            return Dict(__import__("anyconfig").load(self, suffix))
        except FileNotFoundError:
            return {}

    def dump(self, *object, **kwargs):
        if self.is_txt() or self.is_gitignore():
            object = object[0] if object else []
            return self.write_text("\n".join(object))
        object = (kwargs,) + object
        object = merge(*object)
        suffix = self.suffix.lstrip(".")
        suffix = compat.get(suffix, suffix)

        return __import__("anyconfig").dump(object, self, suffix)

    def commit(self, msg, ammend=False):
        return


class Dir(Path):
    def __bool__(self):
        return self.is_dir()


class Module(str):
    def __bool__(self):
        try:
            return False
        except:
            return False


def merge(a, b=None, *extras):
    """merge dictionaries.  """
    b = {} if b is None else b
    if extras:  # reduce the arity until we have a binop
        b = merge(b, *extras)

    if isinstance(a or b, (str, int, float)):
        return a or b
    if isinstance(a or b, (tuple, list)):
        return type(a or b)(a + b)

    a, b = a or {}, b or {}

    for k in set(a).union(b):
        if isinstance(a or b, dict):
            kind = type(a[k] if k in a else b[k])
        else:
            kind = type(a or b)
        if k not in a:
            a[k] = kind()
        if issubclass(kind, dict):
            a[k] = merge(a[k], b.get(k, kind()))
        elif issubclass(kind, set):
            a[k] = a[k].union(b.get(k, kind()))
        elif issubclass(kind, (tuple, list)):
            # assume unique lists
            a[k] += [x for x in b.get(k, kind()) if x not in a[k]]
        else:
            a[k] = a[k] or b.get(k, kind())
    return Dict(a)


def make_conda_pip_envs():
    import json
    import doit

    file = dgaf.File("environment.yml") or dgaf.File("environment.yaml")
    file or make_prior_env()
    reqs = dgaf.File("requirements.txt")
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
            reqs = dgaf.File("requirements.txt")
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


def make_prior_env():
    """create and write conda environment file."""
    dependencies = depfinder()
    channels = ["conda-forge"]
    file = dgaf.File("environment.yml") or dgaf.File("environment.yaml")

    if any(x in dependencies for x in ("panel", "holoviews", "hvplot")):
        channels = ["pyviz"] + channels

    file.dump(
        dgaf.merge(
            file.load(),
            dict(name="notebook", channels=channels, dependencies=list(dependencies)),
        )
    )


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
    deps.discard("dgaf")
    return {x for x in deps if x not in "python"}


def is_site_package(name):
    path = __import__("importlib").find_loader(name).path

    return any(path.startswith(x) for x in __import__("site").getsitepackages())


@dataclasses.dataclass(order=True)
class Task:
    callable: callable
    input: None = None
    output: None = None
    extras: None = dataclasses.field(default_factory=dict)

    def __post_init__(self):
        if self.input == ...:
            self.input = None

        if self.output == ...:
            self.output = None

        for k in "input output callable".split():
            setattr(self, k, getattr(self, k, None) or [])
            if not isinstance(getattr(self, k), list):
                setattr(self, k, [getattr(self, k)])

    def _file_dep(self):
        return [x for x in self.input if isinstance(x, Path)]

    def _task_dep(self):
        return [x.__name__ for x in self.input if callable(x)]

    def _uptodate(self):
        """filter the uptodate dependencies using dict and str values."""
        return [
            doit.tools.config_changed(x)
            for x in self.input
            if isinstance(x, (dict, str))
        ]

    def __call__(self):
        return dict(
            actions=self.callable,
            file_dep=self._file_dep(),
            task_dep=self._task_dep(),
            targets=self.output,
            uptodate=self._uptodate(),
            verbosity=2,
            doc=self.callable[0].__doc__,
            **self.extras,
        )


def task(input, output=None, **extras):
    def wrapped(callable):
        callable.task = Task(callable, input, output, extras)
        callable.create_doit_tasks = callable.task.__call__
        return callable

    return wrapped


def action(*args):
    import doit

    cmd = ""
    for arg in args:
        if isinstance(arg, (set, tuple, list, dict)):
            cmd += " ".join(f'"{x}"' for x in arg)
        else:
            cmd += str(arg)
    return doit.tools.LongRunning(cmd)


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
        dgaf.util.is_installed(object),
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
        object["long_description"] = f"file: {dgaf.base.README}"

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
        object["install_requires"] = dgaf.base.REQUIREMENTS.read_text().splitlines()
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
        if dgaf.base.SRC.exists():
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
