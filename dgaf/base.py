"""base.py"""
import dgaf
import pathlib
import functools
import typing
import jsonpointer
import dataclasses
import doit
import git
import operator

Path = type(pathlib.Path())


class File(dgaf.util.File):
    def load(self):
        for cls in type(self).__subclasses__():
            if self.suffix in cls._suffixes:
                return cls.load(self)
        else:
            raise TypeError(f"Can't load type with suffix: {self.suffix}")

    def dump(self, object):
        for cls in type(self).__subclasses__():
            if self.suffix in cls._suffixes:
                return cls.dump(self, object)
        else:
            raise TypeError(f"Can't dump type with suffix: {self.suffix}")


class INI(File):
    _suffixes = ".ini", ".cfg"

    def load(self):
        object = __import__("configupdater").ConfigUpdater()
        try:
            object.read_string(self.read_text())
        except FileNotFoundError:
            object.read_string("")
        return object

    def dump(self, object):
        self.write_text(str(object))


class TOML(File):
    _suffixes = (".toml",)

    def load(self):
        try:
            return __import__("tomlkit").parse(self.read_text())
        except FileNotFoundError:
            return __import__("tomlkit").parse("")

    def dump(self, object):
        self.write_text(__import__("tomlkit").dumps(object))


class YML(File):
    _suffixes = ".yaml", ".yml", ".json", ".ipynb"

    def load(self):
        object = __import__("ruamel").yaml.YAML()
        try:
            return object.load(self.read_text())
        except FileNotFoundError:
            return {}

    def dump(self, object):
        with self.open("w") as file:
            __import__("ruamel").yaml.YAML().dump(object, file)


@dataclasses.dataclass
class Project:

    """`Project` encapsulates the macroscopic contents of git repository and its history.

    This class can derive configuration and transform configurations."""

    cwd: Path = None
    REPO: git.Repo = None
    FILES: typing.List[Path] = None
    CONTENT: typing.List[Path] = None
    DIRECTORIES: typing.List[Path] = None
    INITS: typing.List[Path] = None

    def __post_init__(self):
        self.REPO = git.Repo(self.cwd)
        self.FILES = list(
            map(dgaf.util.File, git.Git(self.cwd).ls_files().splitlines())
        )
        self.CONTENT = [x for x in self.FILES if x not in dgaf.files.CONVENTIONS]
        self.DIRECTORIES = list(set(map(operator.attrgetter("parent"), self.FILES)))
        self.INITS = [
            x / "__init__.py"
            for x in self.DIRECTORIES
            if (x != dgaf.File()) and (x / "__init__.py" not in self.CONTENT)
        ]

    def create_doit_tasks(self) -> typing.Iterator[dict]:
        yield from self

    def __iter__(self):
        yield from []
