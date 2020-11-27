"""base.py"""
import dgaf
import pathlib
import functools
import textwrap
import typing
import jsonpointer
import dataclasses
import doit
import git
import operator
import os

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
ENVIRONMENT = Convention("environment.yaml") or Convention("environment.yml")

GITHUB = Convention(".github")
GITIGNORE = Convention(".gitignore")
INDEX = File("index.html")
INIT = File("__init__.py")
POETRYLOCK = Convention("poetry.lock")
POSTBUILD = Convention("postBuild")
PYPROJECT = Convention("pyproject.toml")
README = Convention("readme.md")
PYPROJECT = Convention("pyproject.toml")
REQUIREMENTS = Convention("requirements.txt")
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
    REPO: git.Repo = None
    FILES: typing.List[Path] = None
    CONTENT: typing.List[Path] = None
    DIRECTORIES: typing.List[Path] = None
    INITS: typing.List[Path] = None
    SUFFIXES: typing.List[str] = None

    def __post_init__(self):
        self.REPO = git.Repo(self.cwd)
        self.FILES = list(
            map(dgaf.util.File, git.Git(self.cwd).ls_files().splitlines())
        )
        self.CONTENT = [x for x in self.FILES if x not in CONVENTIONS]
        self.DIRECTORIES = list(set(map(operator.attrgetter("parent"), self.FILES)))
        self.INITS = [
            x / "__init__.py"
            for x in self.DIRECTORIES
            if (x != dgaf.File()) and (x / "__init__.py" not in self.CONTENT)
        ]
        self.SUFFIXES = list(set(x.suffix for x in self.FILES))

    def create_doit_tasks(self) -> typing.Iterator[dict]:
        yield from self

    def __iter__(self):
        yield []

    def task(self):
        return doit.cmd_base.ModuleTaskLoader(
            {"DOIT_CFG": DEFAULT_DOIT_CFG, type(self).__name__.lower(): self}
        )

    def main(self):
        return doit.doit_cmd.DoitMain(self.task())


@dataclasses.dataclass
class Start(Project):
    discover: bool = True
    develop: bool = True
    install: bool = False
    test: bool = True
    lint: bool = True
    docs: bool = True
    conda: bool = False
    smoke: bool = True
    ci: bool = False
    pdf: bool = False
    poetry: bool = False
    mamba: bool = False

    def dev_dependencies(self):
        """find the development depdencies we need."""

    def discover_dependencies(self):
        data = SETUPCFG.load()

        for x in "metadata options".split():
            if x not in data:
                data.add_section(x)

        options = data["options"]
        if "install_requires" not in options:
            options["install_requires"] = """"""
        options["install_requires"] = (
            ""  # str(options["install_requires"])
            + "\n"
            + textwrap.indent("\n".join(dgaf.converters.to_deps(self.CONTENT)), " " * 4)
        )

        SETUPCFG.dump(data)

    def init_directories(self):
        for init in self.INITS:
            if init == SRC:
                continue
            if not init:
                init.touch()

    def setup_cfg_to_environment_yml(self):
        dgaf.converters.setup_cfg_to_environment_yml()

    def setup_cfg_to_requirements_txt(self):
        data = SETUPCFG.load()
        if hasattr(data, "to_dict"):
            data = data.to_dict()
        REQUIREMENTS.write_text(data["options"]["install_requires"])

    def to_setup_cfg(self):

        data = SETUPCFG.load()

        for x in "metadata options".split():
            if x not in data:
                data.add_section(x)

        metadata, options = data["metadata"], data["options"]
        if "name" not in metadata:
            metadata["name"] = "test"
        if "version" not in metadata:
            metadata["version"] = (
                __import__("datetime").date.today().strftime("%Y.%m.%d")
            )
        if "description" not in metadata:
            metadata["description"] = ""
        if "long_description" not in metadata:
            metadata["long_description"] = f"file: {README}"

        if "include_package_data" not in options:
            options["include_package_data"] = True
        if "packages" not in options:
            options["packages"] = "find:"

        if SRC in self.DIRECTORIES:
            if "package_dir" not in options:
                options["package_dir"] = """\n    =src"""

            key = "options.packages.find"
            if key not in data:
                data.add_section(key)
                data[key]["where"] = "src"
        # py_modules
        File("setup.cfg").dump(data)

    def to_setup_py(self):
        SETUPPY.write_text("""__import__("setuptools").setup()""".strip())

    def to_pre_commit_config(self):
        data = PRECOMMITCONFIG.load()
        if "repos" not in data:
            data["repos"] = []

        for suffix in [None] + list(set(x.suffix for x in self.FILES)):
            if suffix in LINT_DEFAULTS:
                for kind in LINT_DEFAULTS[suffix]:
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

    def doit_config(self):
        DOITCFG.write_text(
            """[GLOBAL]
backend=sqlite3
par_type=thread
verbosity=2
"""
        )

    def __iter__(self):
        # explicitly configure how do it works.
        config = DOITCFG.load()
        if hasattr(config, "to_dict"):
            config = config.to_dict()
        yield dgaf.util.task("doit.cfg", config, DOITCFG, self.doit_config)

        # seed the setup.cfg declarative configuration file.
        if self.develop or self.install:
            yield dgaf.util.task("setup.cfg", self.CONTENT, SETUPCFG, self.to_setup_cfg)
            yield dgaf.util.task(
                "__init__.py",
                " ".join(sorted(map(str, self.DIRECTORIES))),
                self.INITS,
                self.init_directories,
            )

        # get the current state of the setup.
        state = SETUPCFG.load()

        if self.discover:
            # discover the packages for the project.
            if hasattr(state, "to_dict"):
                state = state.to_dict()

            # discover dependencies in the content with depfinder and append the results.
            yield dgaf.util.task(
                "discover-dependencies",
                self.CONTENT + [state, SETUPCFG],
                ...,
                self.discover_dependencies,
            )

        if self.conda:
            yield dgaf.util.install_task("ensureconda", actions=["ensureconda"])
            yield dgaf.util.task(
                "discover-conda-environment",
                [state, SETUPCFG],
                ENVIRONMENT,
                self.setup_cfg_to_environment_yml,
            )
        elif self.develop or self.install:
            # we'll install these when we make the project.
            pass
        else:
            yield dgaf.util.task(
                "discover-pip-requirements",
                [state, SETUPCFG],
                REQUIREMENTS,
                self.setup_cfg_to_requirements_txt,
            )
            ...

        if self.lint:
            yield dgaf.util.install_task("pre_commit")
            yield dgaf.util.task(
                "infer-pre-commit",
                " ".join(sorted(self.SUFFIXES)),
                PRECOMMITCONFIG,
                self.to_pre_commit_config,
            )
            yield dgaf.util.task(
                "install-pre-commit-hooks",
                [PRECOMMITCONFIG, PRECOMMITCONFIG.load()],
                ...,
                "pre-commit install-hooks",
            )
        if self.test:
            if self.ci:
                extras = []

            if not self.smoke and TOX:
                yield dgaf.util.install_task("tox")
            else:
                yield dgaf.util.install_task("pytest")

        if self.docs:
            yield dgaf.util.install_task("jupyter_book")


LINT_DEFAULTS = {
    None: [
        dict(
            repo="https://github.com/pre-commit/pre-commit-hooks",
            rev="v2.3.0",
            hooks=[dict(id="end-of-file-fixer"), dict(id="trailing-whitespace")],
        )
    ],
    ".yml": [
        dict(
            repo="https://github.com/pre-commit/pre-commit-hooks",
            hooks=[dict(id="check-yaml")],
        )
    ],
    ".py": [
        dict(
            repo="https://github.com/psf/black", rev="19.3b0", hooks=[dict(id="black")]
        ),
        dict(
            repo="https://github.com/life4/flakehell",
            rev="v.0.7.0",
            hooks=[dict(id="flakehell")],
        ),
    ],
}
LINT_DEFAULTS[".yaml"] = LINT_DEFAULTS[".yml"]


@dataclasses.dataclass
class Develop(Start):
    def __iter__(self):
        yield from super().__iter__()

        if self.conda or self.mamba:
            # update the conda environemnt
            yield dgaf.util.task(
                "update-conda",
                ENVIRONMENT,
                ...,
                f"""{
                    self.mamba and "mamba" or "conda"
                } env update -f {ENVIRONMENT}""",
            )
        elif not (self.install or self.develop):
            # update the pip environment
            yield dgaf.util.task(
                "update-pip", REQUIREMENTS, ..., f"pip install -r {REQUIREMENTS}"
            )

        if self.install:
            # install to site packages.
            yield dgaf.util.task("install-package", self.CONTENT, ..., "pip install .")
        elif self.develop:
            # make a setup.py to use in develop mode
            yield dgaf.util.task("setup.py", SETUPCFG, SETUPPY, self.to_setup_py)
            yield dgaf.util.task("develop-package", SETUPPY, ..., "pip install -e .")

        if self.lint:
            yield dgaf.util.task(
                "format-lint", [False], ..., "python -m pre_commit run --all-files"
            )

        if self.test:
            if not self.smoke and TOX:
                # can we infer a good tox test
                yield dgaf.util.task(
                    "test-tox", self.CONTENT + [TOX, False], ..., "tox"
                )
            else:
                yield dgaf.util.task(
                    "test-pytest", self.CONTENT + [PYPROJECT, False], ..., "pytest"
                )

        if self.docs:
            # make toc
            # make config
            yield dgaf.util.task(
                "build-html-docs",
                self.CONTENT + [TOC, CONFIG],
                ["build/html"],
                "jb build .",
            )
