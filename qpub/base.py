"""base.py"""
import qpub
import pathlib
import functools
import textwrap
import typing
import dataclasses
import doit
import distutils.command.sdist
import operator
import os
from qpub.util import task

Path = type(pathlib.Path())


class File(Path):
    """a supercharged file object that make it is easy to dump and load data.

    the loaders and dumpers edit files in-place, these constraints may not apply to all systems.
    """

    def __bool__(self):
        return self.is_file()

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


class Convention(File):
    """Convention types provide an indicator for task targets that
    may cause cyclic dependencies."""


from qpub.files import *


# default conventions for https://pydoit.org/configuration.html
DEFAULT_DOIT_CFG = dict(verbosity=2, backend="sqlite3", par_type="thread")


class Project:
    """A base class for projects."""

    cwd: Path = None
    REPO: "git.Repo" = None
    FILES: typing.List[Path] = None
    CONTENT: typing.List[Path] = None
    DIRECTORIES: typing.List[Path] = None
    INITS: typing.List[Path] = None
    SUFFIXES: typing.List[str] = None
    distribution: distutils.core.Distribution = None
    sdist: distutils.core.Command = None
    bdist: distutils.core.Command = None

    def make_distribution(self):
        import setuptools

        self.distribution = distutils.dist.Distribution(dict())
        self.distribution.parse_config_files()
        self.distribution.script_name = "setup.py"

        self.sdist = self.distribution.get_command_obj("sdist").get_finalized_command(
            "sdist"
        )

        self.sdist.filelist = distutils.command.sdist.FileList()
        self.sdist.get_file_list()
        self.sdist.make_distribution()

        self.bdist = self.distribution.get_command_obj(
            "bdist_wheel"
        ).get_finalized_command("bdist_wheel")
        self.packages = setuptools.find_packages(where=SRC or ".")

    def __post_init__(self):
        import git

        self.REPO = git.Repo(self.cwd)
        self.FILES = list(map(File, git.Git(self.cwd).ls_files().splitlines()))

        for submodule in self.REPO.submodules:
            self.FILES += list(
                File(submodule.path, x.path)
                for x in git.Repo(submodule.path).tree().traverse()
            )
        self.CONTENT = [x for x in self.FILES if x not in CONVENTIONS and x.is_file()]
        self.DIRECTORIES = list(
            x
            for x in set(map(operator.attrgetter("parent"), self.FILES))
            if x not in CONVENTIONS
        )
        self.INITS = [
            x / "__init__.py"
            for x in self.DIRECTORIES
            if (x != ROOT) and (x / "__init__.py" not in self.CONTENT)
        ]
        self.SUFFIXES = list(set(x.suffix for x in self.FILES))
        self.make_distribution()
        self.DISTS = [
            self.sdist.get_archive_files(),
            DIST
            / (
                "-".join(
                    (self.bdist.wheel_dist_name.replace("-", "_"),)
                    + self.bdist.get_tag()
                )
                + ".whl"
            ),
        ]

    def create_doit_tasks(self) -> typing.Iterator[dict]:
        yield from self

    def __iter__(self):
        yield from []

    def task(self):
        return doit.cmd_base.ModuleTaskLoader(
            {"DOIT_CFG": DEFAULT_DOIT_CFG, type(self).__name__.lower(): self}
        )

    def main(self):
        return doit.doit_cmd.DoitMain(self.task())


@dataclasses.dataclass
class Prior(Project):
    """Prior defines tasks needed for installation; it introduces flags to control
    the behavior of `qpub`."""

    discover: bool = True
    develop: bool = True
    install: bool = False
    test: bool = True
    lint: bool = True
    docs: bool = False
    conda: bool = False
    smoke: bool = True
    ci: bool = False
    pdf: bool = False
    poetry: bool = False
    mamba: bool = False
    binder: bool = False
    pep517: bool = True

    def setup_cfg_to_environment_yml(self):
        qpub.converters.setup_cfg_to_environment_yml()

    def __iter__(self):
        if self.develop or self.install:
            yield from qpub.tasks.Develop.prior(self)

        if self.discover:
            # discover dependencies in the content with depfinder and append the results.
            yield from qpub.tasks.Discover.prior(self)

        if self.conda:
            yield from qpub.tasks.Conda.prior(self)
        elif self.develop or self.install:
            pass
        else:
            yield from qpub.tasks.Pip.prior(self)

        if self.lint:
            yield from qpub.tasks.Precommit.prior(self)


@dataclasses.dataclass
class Distribution(Prior):
    """Distribution defines tasks needed for installation."""

    def __iter__(self):
        yield from super().__iter__()

        if self.conda or self.mamba:
            # update the conda environemnt
            yield from qpub.tasks.Conda.post(self)
        elif not (self.install or self.develop):
            # update the pip environment
            yield from qpub.tasks.Pip.post(self)

        if self.install:
            # install to site packages.
            yield from qpub.tasks.Install.post(self)

        elif self.develop:
            # make a setup.py to use in develop mode
            yield from qpub.tasks.Develop.post(self)

        if self.lint:
            yield from qpub.tasks.Precommit.post(self)

        if self.test:
            yield from qpub.tasks.Test.post(self)

        if self.docs:
            yield from qpub.tasks.Docs.post(self)
