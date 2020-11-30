"""base.py"""
import dgaf
import pathlib
import functools
import textwrap
import typing
import dataclasses
import doit
import distutils.command.sdist
import operator
import os
from dgaf.util import task

Path = type(pathlib.Path())


class File(dgaf.util.File):
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
    ...


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
        self.write_text(str(object) + "\n")


class TOML(File):
    _suffixes = (".toml",)

    def load(self):
        try:
            return __import__("tomlkit").parse(self.read_text())
        except FileNotFoundError:
            return __import__("tomlkit").parse("")

    def dump(self, object):
        self.write_text(__import__("tomlkit").dumps(object) + "\n")


class YML(File):
    _suffixes = ".yaml", ".yml", ".json", ".ipynb"

    def load(self):
        object = __import__("ruamel.yaml").yaml.YAML()
        try:
            return object.load(self.read_text())
        except FileNotFoundError:
            return {}

    def dump(self, object):
        with self.open("w") as file:
            __import__("ruamel").yaml.YAML().dump(object, file)


# File conventions.
DEFAULT_DOIT_CFG = dict(verbosity=2, backend="sqlite3", par_type="thread")
CONF = Convention("conf.py")
DOCS = Convention("docs")  # a convention with precedence from github
CONFIG = Convention("_config.yml") or DOCS / "_config.yml"
TOC = Convention("_toc.yml") or DOCS / "_toc.yml"
DODO = Convention("dodo.py")
DOITCFG = Convention("doit.cfg")
DIST = Convention("dist")
ENVIRONMENT = Convention("environment.yaml") or Convention("environment.yml")

GITHUB = Convention(".github")
GITIGNORE = Convention(".gitignore")
INDEX = File("index.html")
INIT = File("__init__.py")
POETRYLOCK = Convention("poetry.lock")
POSTBUILD = Convention("postBuild")
PYPROJECT = Convention("pyproject.toml")
MANIFESTIN = Convention("MANIFEST.in")
ROOT = Convention()
README = Convention("readme.md") or Convention("README.md")
PYPROJECT = Convention("pyproject.toml")
REQUIREMENTS = Convention("requirements.txt")
REQUIREMENTSDEV = Convention("requirements-dev.txt")
SETUPPY = Convention("setup.py")
SETUPCFG = Convention("setup.cfg")
SRC = Convention("src")
TOX = Convention("tox.ini")
WORKFLOWS = GITHUB / "workflows"

OS = os.name
PRECOMMITCONFIG = Convention(".pre-commit-config.yaml")
BUILT_SPHINX = File("_build/sphinx")
CONVENTIONS = [x for x in locals().values() if isinstance(x, Convention)]


class Project:
    """A base class for projects the creates doit tasks for development environments."""

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

    def get_name(self):
        return "rip-testum"

    def get_version(self):
        return __import__("datetime").date.today().strftime("%Y.%m.%d")

    def __post_init__(self):
        import git

        self.REPO = git.Repo(self.cwd)
        self.FILES = list(
            map(dgaf.util.File, git.Git(self.cwd).ls_files().splitlines())
        )
        self.CONTENT = [x for x in self.FILES if x not in CONVENTIONS]
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
        self.DISTS = [
            DIST / f"{self.get_name()}-{self.get_version()}.tar.gz",
            DIST
            / f"{self.get_name().replace('-', '_')}-{self.get_version()}-py3-none-any.whl",
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
    pep517: bool = True

    def __post_init__(self):
        super().__post_init__()
        self.make_distribution()

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

    def dev_dependencies(self):
        """find the development depdencies we need."""
        deps = []
        if self.smoke:
            deps += ["pytest"]
        elif TOX:
            deps += ["tox"]
        if self.pep517:
            deps += ["pep517"]
        else:
            deps += ["setuptools", "wheel"]

        if self.lint:
            deps += ["pre_commit"]

        if self.poetry and self.develop:
            deps += ["poetry"]

        if self.conda:
            deps += ["ensureconda"]

        if self.mamba:
            deps += ["mamba"]

        if self.docs:
            deps += ["jupyter_book"]
        return deps

    def create_manifest(self):
        MANIFESTIN.touch()

    def discover_dependencies(self):
        import pkg_resources

        prior = []
        for line in REQUIREMENTS.read_text().splitlines():
            try:
                prior.append(pkg_resources.Requirement(line).name.lower())
            except pkg_resources.extern.packaging.requirements.InvalidRequirement:
                ...

        found = [
            x for x in dgaf.converters.to_deps(self.CONTENT) if x.lower() not in prior
        ]
        with REQUIREMENTS.open("a") as file:
            file.write("\n" + "\n".join(found))

    def init_directories(self):
        for init in self.INITS:
            if init == SRC:
                continue
            if not init:
                init.touch()

    def setup_cfg_to_environment_yml(self):
        dgaf.converters.setup_cfg_to_environment_yml()

    def setup_cfg_to_pyproject(self):

        data = PYPROJECT.load()
        data.update(
            {
                "build-system": {
                    "requires": ["setuptools", "wheel"],
                    "build-backend": "setuptools.build_meta",
                }
            }
        )
        PYPROJECT.dump(data)

    def to_setup_cfg(self):
        data = dgaf.base.SETUPCFG.load()
        config = dgaf.util.to_metadata_options(self)

        for k, v in config.items():
            if k not in data:
                data.add_section(k)
            for x, y in v.items():
                if isinstance(y, list):
                    y = "\n" + __import__("textwrap").indent("\n".join(y), " " * 4)
                if x in data[k]:
                    if data[k][x] == y:
                        # consider merging here.
                        continue
                data[k][x] = y

        # add a tool:pytest
        # https://docs.pytest.org/en/stable/customize.html#finding-the-rootdir

        dgaf.base.SETUPCFG.dump(data)

    def to_setup_py(self):
        # https://setuptools.readthedocs.io/en/latest/userguide/declarative_config.html#configuring-setup-using-setup-cfg-files
        SETUPPY.write_text("""__import__("setuptools").setup()""".strip())

    def to_pre_commit_config(self):
        data = PRECOMMITCONFIG.load()
        if "repos" not in data:
            data["repos"] = []

        for suffix in [None] + list(set(x.suffix for x in self.FILES)):
            if suffix in dgaf.tasks.LINT_DEFAULTS:
                for kind in dgaf.tasks.LINT_DEFAULTS[suffix]:
                    for repo in data["repos"]:
                        if repo["repo"] == kind["repo"]:
                            repo["rev"] = repo.get("rev", None) or kind.get("rev", None)

                            ids = set(x["id"] for x in kind["hooks"])
                            repo["hooks"] = repo["hooks"] + [
                                x for x in kind["hooks"] if x["id"] not in ids
                            ]
                            break
                    else:
                        data["repos"] += [dict(kind)]

        PRECOMMITCONFIG.dump(data)

    def __iter__(self):
        # explicitly configure how do it

        # seed the setup.cfg declarative configuration file.

        if self.develop or self.install:
            yield from dgaf.tasks.Develop.prior(self)

        if self.discover:
            # discover dependencies in the content with depfinder and append the results.
            yield from dgaf.tasks.Discover.prior(self)

        if self.conda:
            yield from dgaf.tasks.Conda.prior(self)
        elif self.develop or self.install:
            # we'll install these when we make the project.
            if self.pep517:
                yield from dgaf.tasks.PEP517.prior(self)
        else:
            yield from dgaf.tasks.Pip.prior(self)


@dataclasses.dataclass
class Distribution(Prior):
    def __iter__(self):
        yield from super().__iter__()

        if self.conda or self.mamba:
            # update the conda environemnt
            yield from dgaf.tasks.Conda.post(self)
        elif not (self.install or self.develop):
            # update the pip environment
            yield from dgaf.tasks.Pip.post(self)

        if self.install:
            # install to site packages.
            if self.pep517:
                yield from dgaf.tasks.PEP517.post(self)
            else:
                yield from dgaf.tasks.Install.post(self)

        elif self.develop:
            # make a setup.py to use in develop mode
            yield from dgaf.tasks.Develop.post(self)

        if self.lint:
            yield from dgaf.tasks.Precommit.post(self)

        if self.test:
            yield from dgaf.tasks.Test.post(self)

        if self.docs:
            yield from dgaf.tasks.Docs.post(self)
