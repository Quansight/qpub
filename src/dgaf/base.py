import collections
import dataclasses
import importlib
import io
import sys

from . import DOIT_CONFIG
from .files import CONVENTIONS, GIT, SRC, File, Path, DOCS, File

BUILDSYSTEM = "build-system"


class options:
    cache = Path(__file__).parent / "_data"


def get_repo():
    if GIT.exists():
        import git

        return git.Repo()


@dataclasses.dataclass
class Repo:
    repo: object = dataclasses.field(default_factory=get_repo)

    def get_email(self):
        if self.repo:
            return self.repo.commit().author.email
        return ""

    def get_author(self):
        if self.repo:
            return self.repo.commit().author.name
        return ""

    def get_url(self):
        if self.repo:
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


def get_name(common={File("notebooks"), File("docs"), File("posts"), File("tests")}):
    is_common = []
    if SRC.exists():
        for x in SRC.iterdir():
            if is_private(x):
                continue
            if x.is_dir():
                return x.stem

        raise Exception

    for directory in [True, False]:
        for x in Path().iterdir():

            if directory:
                if x in common:
                    is_common.append(x)
                    continue

            if is_private(x):
                continue

            if x in CONVENTIONS:
                continue

            if directory:
                if x.is_dir():
                    return x.stem
            else:
                if x.suffix in {".py", ".ipynb"}:
                    return x.stem
    else:
        if is_common:
            return is_common.pop(0)

    raise Exception


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
        if isinstance(self.dir, str):
            self.dir = Path(self.dir)
        self.get_include_exclude()
        self.directories = sorted(set(x.parent for x in self.include))
        self.include = sorted(set(x for x in self.include if x not in self.directories))
        self.exclude_patterns = sorted(set(self.exclude_patterns))

        self.suffixes = sorted(set(x.suffix for x in self.include if x.suffix))
        self.exclude_directories = sorted(set(x for x in self.exclude if x.is_dir()))

    def source_files(self):
        """filter the source files"""
        if SRC.exists():
            return [x for x in self.include if x.is_relative_to(SRC)]
        name = Path(get_name())
        if Path(name).exists():
            return [x for x in self.include if x.is_relative_to(SRC)]
        return self.include

    def test_files(self):
        """filter the test files"""
        return [x for x in self.include if x.stem.startswith("test_")]

    def docs_files(self):
        """filter the documentation files"""
        if DOCS:
            return [x for x in self.include if x.is_relative_to(DOCS)]
        return []

    def get_include_exclude(self, dir=None, files=None):
        """split the included and excluded files"""
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


def is_private(object, chars=".-"):
    """is the file name hidden or private"""
    return Path(object).stem.startswith(tuple(chars))


def get_license():
    """get the license"""
    return ""


def get_python_version():
    """get the python version"""
    import sys

    return f"{sys.version_info.major}.{sys.version_info.minor}"


def get_module(name):
    import flit

    return flit.common.Module(get_name())


def get_version():
    """get the project version"""
    import datetime

    import flit

    try:
        x = flit.common.get_info_from_module(get_module(get_name())).pop("version")
    except:
        x = datetime.date.today().strftime("%Y.%m.%d")
    return normalize_version(x)


def normalize_version(object):
    """normalize the version number"""
    import contextlib

    import packaging.requirements

    with contextlib.redirect_stdout(io.StringIO()):
        return str(packaging.version.Version(object))


def get_description():
    """get the project description"""
    import flit

    return flit.common.get_info_from_module(get_module(get_name())).pop("summary")


def main(object=None, argv=None, raises=False):
    """a generic runner for tasks in process."""

    global DOIT_CONFIG
    import sys

    import doit
    from . import __main__

    if object is None:

        object = __main__.load_tasks()

    if callable(object):
        object = [object]

    if isinstance(object, list):
        # use a list of callables or strings to define the default tasks
        default_tasks = [
            x if isinstance(x, str) else x.__name__[len("task_") :] for x in object
        ]

        # load the tasks and default tasks
        object = __main__.load_tasks()

        # override default tasks
        DOIT_CONFIG["default_tasks"] = default_tasks

        # avoid using the sys args
        argv = argv or []

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
    return code


def needs(*object):
    """a function designed install packages as needed"""
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
    """locate the qpub jsone-e templates"""
    try:
        with importlib.resources.path("dgaf.templates", template) as template:
            template = File(template)
    except:
        template = File(__file__).parent / "templates" / template
    return template


def templated_file(template, data):
    """return the templated data based on a template"""
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
    """return the pattern that ignores the object"""
    for k, v in ignore().items():
        try:
            next(v.match([str(object)]))
            return k
        except StopIteration:
            continue


def ignored(object):
    """return True when the object ignored"""
    return bool(ignored_by(object))
