import dgaf
import pathlib
import functools
import jsonpointer

Path = type(pathlib.Path())

compat = {"yml": "yaml", "cfg": "ini"}
pkg2pip = dict(git="GitPython", dotenv="python-dotenv")


class Dict(dict):
    def __getitem__(self, object):
        try:
            pointer = jsonpointer.JsonPointer(object)
        except jsonpointer.JsonPointerException:
            return super().__getitem__(object)
        else:
            try:
                return pointer.resolve(self)
            except (KeyError, jsonpointer.JsonPointerException):
                return

    def get(self, object, default=None):
        try:
            return self[object]
        except (KeyError, jsonpointer.JsonPointerException):
            ...
        return default

    def __setitem__(self, object, value):
        try:
            pointer = jsonpointer.JsonPointer(object)
        except jsonpointer.JsonPointerException:
            ...
        else:
            return pointer.set(self, value)
        return super().__setitem__(object, value)


def squash_depfinder(object):
    import depfinder

    if isinstance(object, tuple):
        object = object[-1]
    if isinstance(object, depfinder.main.ImportFinder):
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


def merge(a, b, *extras):
    """merge dictionaries.  """
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


def make_pyproject():
    import git

    author = git.Repo().commit().author

    metadata = dgaf.dodo.PYPROJECT.get("tool", {}).get("flit", {}).get("metadata", {})
    metadata["module"] = metadata.get("module", "") or "readme"
    metadata["author"] = metadata.get("author", "") or author.name
    metadata["author-email"] = metadata.get("author", "") or author.email
    metadata["homepage"] = "http://"
    # add requirements
    dgaf.File("pyproject.toml").dump(dgaf.dodo.PYPROJECT)


def depfinder(*files) -> set:
    """Find the dependencies for all of the content."""
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


import dataclasses


@dataclasses.dataclass(order=True)
class Task:
    callable: callable
    input: None = None
    output: None = None
    extras: None = dataclasses.field(default_factory=dict)

    def __post_init__(self):
        if self.input == ...:
            self.input = None
        self.input = self.input or []
        if not isinstance(self.input, list):
            self.input = [self.input]

        if self.output == ...:
            self.output = None
        self.output = self.output or []
        if not isinstance(self.output, list):
            self.output = [self.output]

    def __call__(self):
        import doit

        return dict(
            actions=[self.callable],
            file_dep=[x for x in self.input if isinstance(x, (Path, str))],
            task_dep=[x.__name__ for x in self.input if callable(x)],
            targets=self.output,
            verbosity=2,
            doc=self.callable.__doc__,
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