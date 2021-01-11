import collections
import dataclasses
import importlib
import io

from . import DOIT_CONFIG
from .files import CONVENTIONS, GIT, SRC, File, Path

BUILDSYSTEM = "build-system"


class options:
    cache = Path(__file__).parent / "_data"


@dataclasses.dataclass
class Repo:
    repo: object

    def get_email(self):
        return self.repo.commit().author.email

    def get_author(self):
        return self.repo.commit().author.name

    def get_url(self):
        if hasattr(self.repo.remotes, "origin"):
            return self.repo.remotes.origin.url
        return ""

    def get_branch(self):
        self.repo


class Dict(dict):
    __annotations__ = {}

    def __post_init__(self):
        for x in self.__annotations__:
            self[x] = getattr(self, x)
        for i, value in enumerate(self.get("uptodate", {})):
            if isinstance(value, (str, dict)):
                import doit

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
    clean: bool = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Param(Dict):
    name: str
    default: object
    long: str = None
    short: str = None
    type: type = None
    help: str = None
    choices: tuple = dataclasses.field(default_factory=tuple)


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


def get_license():
    return ""


def get_python_version():
    import sys

    return "{sys.version_info.major}.{sys.version_info.minor}"


def get_module(name):
    import flit

    try:
        return flit.common.Module(get_name())
    except:
        pass


def get_version():
    import datetime

    import flit

    try:
        x = flit.common.get_info_from_module(get_module(get_name())).pop("version")
    except:
        x = datetime.date.today().strftime("%Y.%m.%d")
    return normalize_version(x)


def normalize_version(object):
    import contextlib

    import packaging.requirements

    with contextlib.redirect_stdout(io.StringIO()):
        return str(packaging.version.Version(object))


def get_description():
    import flit

    return flit.common.get_info_from_module(get_module(get_name())).pop("summary")


@dataclasses.dataclass
class Chapter:
    __annotations__ = {}
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
        self.exclude_directories = sorted(set(x.parent for x in []))

    def source_files(self):
        return self.include

    def test_files(self):
        return self.include

    def docs_files(self):
        return self.include

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
    import sys

    import doit

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
        ).execute(sys.stdout, sys.stderr)


def where_template(template):
    try:
        with importlib.resources.path("dgaf.templates", template) as template:
            template = File(template)
    except:
        template = File(__file__).parent / "templates" / template
    return template


def templated_file(template, data):
    import jsone

    return jsone.render(where_template(template).load(), data)


def ignore(cache={}):
    """initialize the path specifications to decide what to omit."""
    import importlib.resources

    if cache:
        return cache

    for file in ("Python.gitignore", "Nikola.gitignore", "JupyterNotebooks.gitignore"):
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
