"""q(uick) p(ubishing) configures python Project and documentaton tools.

"""
#    ___    ____      _   _    ____
#   / " \ U|  _"\ uU |"|u| |U | __")u
#  | |"| |\| |_) |/ \| |\| | \|  _ \/
# /| |_| |\|  __/    | |_| |  | |_) |
# U \__\_\u|_|      <<\___/   |____/
#    \\//  ||>>_   (__) )(   _|| \\_
#   (_(__)(__)__)      (__) (__) (__)

import dataclasses
import io
import collections
import functools
import itertools

try:
    import importlib.resources
except ModuleNotFoundError:
    import importlib, importlib_resources

    importlib.resource = importlib_resources

try:
    import importlib.metadata
except ModuleNotFoundError:
    import importlib, importlib_metadata

    importlib.metadata = importlib_metadata

__version__ = __import__("datetime").date.today().strftime("%Y.%m.%d")

Path = type(__import__("pathlib").Path())

if not hasattr(Path, "is_relative_to"):

    def _is_relative_to(self, *objects):
        for object in objects:
            try:
                self.relative_to(object)
                return True
            except:
                pass
        return False

    Path.is_relative_to = _is_relative_to


class options:
    cache = Path(__file__).parent / "_data"


class File(Path):
    """a supercharged file object that make it is easy to dump and load data.

    the loaders and dumpers edit files in-place, these constraints may not apply to all systems.
    """

    def write(self, object):
        self.write_text(self.dump(object))

    def update(self, object):
        return self.write(merge(self.read(), object))

    def load(self):
        """a permissive method to load data from files and edit documents in place."""
        for cls in File.__subclasses__():
            if hasattr(cls, "_suffixes"):
                if self.suffix in cls._suffixes:
                    return cls.load(self)
        else:
            raise TypeError(f"Can't load type with suffix: {self.suffix}")

    def dump(self, object):
        """a permissive method to dump data from files and edit documents in place."""
        for cls in File.__subclasses__():
            if hasattr(cls, "_suffixes"):
                if self.suffix in cls._suffixes:
                    return cls.dump(self, object)
        else:
            raise TypeError(f"Can't dump type with suffix: {self.suffix}")

    __add__, read = update, load


class Convention(File):
    """a convention indicates explicit or implicit filename and directory conventions.

    the conventions were introduced to separate non-canonical content from canonical configuration files.
    if content and configurations are mixed they doit will experience break with cyclic graphs.
    """


DOIT_DB_DAT = Convention(".doit.db.dat")
DOIT_DB_DIR = DOIT_DB_DAT.with_suffix(".dir")
DOIT_DB_BAK = DOIT_DB_DAT.with_suffix(".bak")

PRECOMMITCONFIG_YML = Convention(".pre-commit-config.yaml")
PYPROJECT_TOML = Convention("pyproject.toml")
REQUIREMENTS_TXT = Convention("requirements.txt")
SETUP_CFG = Convention("setup.cfg")
SETUP_PY = Convention("setup.py")
SRC = Convention("src")
GIT = Convention(".git")
GITIGNORE = Convention(".gitignore")
DOCS = Convention("docs")
BUILD = DOCS / "_build"  # abides the sphinx gitignore convention.
TOC = DOCS / "_toc.yml"
CONFIG = DOCS / "_config.yml"
CONF = Convention("conf.py")
CONFTEST = Convention("conftest.py")
NOXFILE = Convention("noxfile.py")
DODO = Convention("dodo.py")
POETRY_LOCK = Convention("poetry.lock")
MKDOCS = Convention("mkdocs.yml")  # https://www.mkdocs.org/
DIST = Convention("dist")
JUPYTEXT = Convention("jupytext.toml")
MANIFEST = Convention("MANIFEST.in")
ENVIRONMENT_YML = Convention("environment.yml")
ENVIRONMENT_YAML = Convention("environment.yaml")
GITHUB = Convention(".github")
WORKFLOWS = GITHUB / "workflows"
BUILDTESTRELEASE = WORKFLOWS / "build_test_release.yml"
READTHEDOCS = Convention(".readthedocs.yml")

CONVENTIONS = [x for x in locals().values() if isinstance(x, Convention)]


BUILDSYSTEM = "build-system"


class Dict(dict):
    def __post_init__(self):
        for x in self.__annotations__:
            self[x] = getattr(self, x)
        for i, value in enumerate(self.get("uptodate", {})):
            if isinstance(value, (str, dict)):
                value = doit.tools.config_changed(value)
            self["uptodate"][i] = value


@dataclasses.dataclass
class Task(Dict):
    file_dep: list = dataclasses.field(default_factory=list)
    targets: list = dataclasses.field(default_factory=list)
    actions: list = dataclasses.field(default_factory=list)
    task_dep: list = dataclasses.field(default_factory=list)
    uptodate: list = dataclasses.field(default_factory=list)
    params: list = dataclasses.field(default_factory=list)
    pos_arg: str = None


@dataclasses.dataclass
class Param(Dict):
    name: str
    default: object
    long: str = None
    short: str = None
    type: type = None
    help: str = None
    choices: tuple = dataclasses.field(default_factory=tuple)


DOIT_CONFIG = dict(verbosity=2, default_tasks=[])


def get_repo():
    if GIT.exists():
        import git

        return git.Repo()


def get_name():
    if SRC.exists():
        for x in SRC.iterdir():
            if is_private(x):
                continue
            if x.is_dir():
                return x.stem

        raise Exception

    for directory in [True, False]:
        for x in Path().iterdir():

            if is_private(x):
                continue

            if x not in CONVENTIONS:
                continue

            if directory:
                if x.is_dir():
                    return x.stem
            else:
                return x.stem
    raise Exception


def is_private(object):
    return Path(object).stem.startswith(tuple(".-"))


def get_module(name):
    import flit

    try:
        return flit.common.Module(get_name())
    except:
        pass


def get_version():
    import flit
    import datetime

    try:
        return flit.common.get_info_from_module(get_module(get_name())).pop("version")
    except:
        return datetime.date.today().strftime("%Y.%m.%d")


def normalize_version(object):
    import packaging.requirements
    import contextlib

    with contextlib.redirect_stdout(io.StringIO()):
        return str(packaging.version.Version(object))


def get_description():
    import flit

    return flit.common.get_info_from_module(get_module(get_name())).pop("summary")


@dataclasses.dataclass
class Chapter:
    dir: str = dataclasses.field(default_factory=Path)
    repo: object = dataclasses.field(default_factory=get_repo)
    include: list = dataclasses.field(default_factory=list)
    exclude: list = dataclasses.field(default_factory=list, repr=False)
    exclude_patterns: list = dataclasses.field(default_factory=list)
    suffixes: list = dataclasses.field(default_factory=list)
    directories: list = dataclasses.field(default_factory=list, repr=False)
    exclude_directories: list = dataclasses.field(default_factory=list, repr=False)

    def __post_init__(self):
        self.get_include_exclude()
        self.directories = sorted(set(x.parent for x in self.include))
        self.include = sorted(set(x for x in self.include if x not in self.directories))
        self.exclude_patterns = sorted(set(self.exclude_patterns))

        self.suffixes = sorted(set(x.suffix for x in self.include if x.suffix))
        self.exclude_directories = sorted(set(x.parent for x in self.exclude))

    def get_include_exclude(self, dir=None, files=None):
        dir = dir or self.dir
        root = files is None
        files = [] if root else files
        for x in dir.iterdir():
            by = ignored_by(str(x))
            if x.is_dir():
                by = ignored_by(str(x))
                if not by:
                    by = ignored_by(x.relative_to(dir) / ".tmp")
                if by:
                    self.exclude_patterns.append(by)
                    self.exclude.append(x)
                else:
                    self.get_include_exclude(x, files)

                continue

            if not by:
                by = ignored_by(str(x.relative_to(dir)))

            if by:
                self.exclude.append(x)
            else:
                self.include.append(x)

    def dump(self):
        return {
            x: [str(x) for x in getattr(self, x)]
            if isinstance(getattr(self, x), list)
            else str(getattr(self, x))
            for x in self.__annotations__
        }

    def _repr_json_(self):
        return self.dump()


def main(object=None, argv=None, raises=False):
    """run the main program"""
    global DOIT_CONFIG
    import doit
    import sys

    if argv is None:
        argv = sys.argv[1:]

    if isinstance(argv, str):
        argv = argv.split()

    class Reporter(doit.reporter.ConsoleReporter):
        def execute_task(self, task):
            self.outstream.write("MyReporter --> %s\n" % task.title())

    DOIT_CONFIG["reporter"] = Reporter
    main = doit.doit_cmd.DoitMain(doit.cmd_base.ModuleTaskLoader(object))

    code = main.run(argv)
    if raises:
        sys.exit(code)


def ensure_trailing_eol(callable):
    """a decorator to comply with our linting opinion."""
    import functools

    @functools.wraps(callable)
    def main(object):
        str = callable(object)
        return str.rstrip() + "\n"

    return main


def load_txt(str):
    return str.splitlines()


def dump_txt(object):
    if isinstance(object, list):
        object = "\n".join(object)
    return object


def load_config(str):
    object = configupdater.ConfigUpdater()
    object.read_string(str)
    return expand_cfg(object)


@ensure_trailing_eol
def dump_config__er(object):
    next = io.StringIO()
    object = compact_cfg(object)
    if isinstance(object, dict):
        import configparser

        parser = configparser.ConfigParser(default_section=None)
        parser.read_dict(object)
        object = parser
    object.write(next)
    return next.getvalue()


def expand_cfg(object):
    """special conditions for config files so configparser and configuupdates work together."""
    for main, section in object.items():
        for key, value in section.items():
            if isinstance(value, str) and value.startswith("\n"):
                value = textwrap.dedent(value).splitlines()[1:]
            object[main][key] = value
    return object


def compact_cfg(object):
    for main, section in object.items():
        for key, value in section.items():
            if isinstance(value, list):
                import textwrap

                value = textwrap.indent(
                    "\n".join([""] + list(map(textwrap.dedent, value))), " " * 4
                )
            object[main][key] = value
    return object


def load_text(str):
    return [x for x in str.splitlines()]


@ensure_trailing_eol
def dump_text(object):
    return "\n".join(object)


def load_toml(str):
    import tomlkit

    return tomlkit.parse(str)


@ensure_trailing_eol
def dump_toml(object):
    import tomlkit

    return tomlkit.dumps(object)


def load_yaml(str):
    import ruamel.yaml

    object = ruamel.yaml.YAML()
    return object.load(str)


@ensure_trailing_eol
def dump_yaml(object):
    import ruamel.yaml

    if isinstance(object, collections.OrderedDict):
        return ruamel.yaml.round_trip_dump(object)
    return ruamel.yaml.safe_dump(object)


def to_dict(object):
    if hasattr(object, "items"):
        data = {}
        for k, v in object.items():
            if k is None:
                continue
            data[k] = to_dict(v)
        else:
            return data
    return object


class INI(File):
    """dump and load ini files in place."""

    _suffixes = ".ini", ".cfg"

    def load(self):
        try:
            return load_config(self.read_text())
        except FileNotFoundError:
            return load_config("")

    def dump(self, object):
        return dump_config__er(object)


class TXT(File):
    """dump and load ini files in place."""

    _suffixes = (".txt",)

    def load(self):
        try:
            return load_txt(self.read_text())
        except FileNotFoundError:
            return load_txt("")

    def dump(self, object):
        return dump_txt(object)


class TOML(File):
    """dump and load toml files in place."""

    _suffixes = (".toml",)

    def load(self):
        try:
            return load_toml(self.read_text())
        except FileNotFoundError:
            return load_toml("")

    def dump(self, object):
        return dump_toml(object)


class JSON(File):
    _suffixes = (".json",)

    def load(self):
        return json.loads(self.read_text())

    def dump(self, boject):
        return json.dumps(object)


class YML(File):
    """dump and load yml files in place."""

    _suffixes = ".yaml", ".yml"

    def load(self):
        try:
            return load_yaml(self.read_text())
        except FileNotFoundError:
            return load_yaml("{}")

    def dump(self, object):
        return dump_yaml(object)


def needs(*object):
    import doit

    needs = []
    for x in object:
        try:
            importlib.resources.distribution(x)
        except:
            needs.append(x)
    if needs:
        assert not doit.tools.CmdAction(
            f"""pip install {" ".join(needs)} --no-deps"""
        ).execute()


def merge(*args):
    import functools

    if not args:
        return {}
    if len(args) == 1:
        return args[0]
    a, b, *args = args
    if args:
        b = functools.reduce(merge, (b, *args))
    if hasattr(a, "items"):
        for k, v in a.items():
            if k in b:
                a[k] = merge(v, b[k])
        for k, v in b.items():
            if k not in a:
                try:
                    a[k] = v
                except ValueError as exception:
                    if hasattr(a, "add_section"):
                        a.add_section(k)
                        a[k].update(v)
                    else:
                        raise exception
        return a
    if isinstance(a, tuple):
        return a + tuple(x for x in b if x not in a)
    if isinstance(a, list):
        return a + list(x for x in b if x not in a)
    if isinstance(a, set):
        return list(sorted(set(a).union(b)))
    return a or b


def ignore(cache={}):
    """initialize the path specifications to decide what to omit."""
    import importlib.resources

    if cache:
        return cache

    def where_template(template):
        try:
            with importlib.resources.path("dgaf.templates", template) as template:
                template = Path(template)
        except:
            template = Path(__file__).parent / "templates" / template
        return template

    for file in (
        "Python.gitignore",
        "Nikola.gitignore",
        "JupyterNotebooks.gitignore",
    ):
        import pathspec

        file = where_template(file)
        for pattern in (
            file.read_text().splitlines()
            + ".local .vscode _build .gitignore .git .doit.db* .benchmarks".split()
        ):
            if bool(pattern):
                match = pathspec.patterns.GitWildMatchPattern(pattern)
                if match.include:
                    cache[pattern] = match
    return cache


def ignored_by(object):
    for k, v in ignore().items():
        try:
            next(v.match([str(object)]))
            return k
        except StopIteration:
            continue


def ignored(object):
    return bool(ignored_by(object))
