"""base.py"""
import dgaf
import pathlib
import functools
import textwrap
import typing
import jsonpointer
import dataclasses
import doit
import distutils.command.sdist
import git
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
    distribution: distutils.core.Distribution = None
    sdist: distutils.core.Command = None
    bdist: distutils.core.Command = None

    def get_name(self):
        return "rip-testum"

    def get_version(self):
        return __import__("datetime").date.today().strftime("%Y.%m.%d")

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
class Init(Project):
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
        self.modules = setuptools.find_packages(where=SRC or ".")

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
            deps += ["pre-commit"]

        if self.poetry and self.develop:
            deps += ["poetry"]

        if self.conda:
            deps += ["ensureconda"]

        if self.mamba:
            deps += ["mamba"]

        if self.docs:
            deps += ["jupyter-book"]
        return deps

    def create_manifest(self):
        MANIFESTIN.touch()

    def discover_dependencies(self):
        REQUIREMENTS.write_text("\n".join(dgaf.converters.to_deps(self.CONTENT)))

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

        data = SETUPCFG.load()

        for x in "metadata options".split():
            if x not in data:
                data.add_section(x)

        metadata, options = data["metadata"], data["options"]
        if "name" not in metadata:
            metadata["name"] = self.get_name()
        if "version" not in metadata:
            metadata["version"] = self.get_version()
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
        # explicitly configure how do it

        # seed the setup.cfg declarative configuration file.
        if self.develop or self.install:
            yield from Develop.prior(self)

        if self.discover:
            # discover dependencies in the content with depfinder and append the results.
            yield from Discover.prior(self)

        if self.conda:
            yield from Conda.prior(self)
        elif self.develop or self.install:
            # we'll install these when we make the project.
            pass
        else:
            yield from Pip.prior(self)
            ...
        if self.lint:
            yield from Precommit.prior(self)
        if self.test:
            yield from Test.prior(self)

        if self.docs:
            yield from Docs.prior(self)


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
class Tasks(Init):
    def __iter__(self):
        yield from super().__iter__()

        if self.conda or self.mamba:
            # update the conda environemnt
            yield Conda.post(self)
        elif not (self.install or self.develop):
            # update the pip environment
            yield from Pip.post(self)

        if self.install:
            # install to site packages.
            if self.pep517:
                yield from PEP517.post(self)
            else:
                yield from Install.post(self)

        elif self.develop:
            # make a setup.py to use in develop mode
            yield from Develop.post(self)

        if self.lint:
            yield from Precommit.post(self)

        if self.test:
            yield from Test.post(self)

        if self.docs:
            yield from Docs.post(self)


class Precommit(Tasks):
    def prior(self):
        yield task(
            "infer-pre-commit",
            self.CONTENT + [" ".join(sorted(self.SUFFIXES))],
            PRECOMMITCONFIG,
            self.to_pre_commit_config,
        )
        yield task(
            "install-pre-commit-hooks",
            [PRECOMMITCONFIG, PRECOMMITCONFIG.load()],
            ...,
            "pre-commit install-hooks",
        )

    def post(self):
        yield task("format-lint", [False], ..., "python -m pre_commit run --all-files")


class Test(Tasks):
    def prior(self):

        if not self.smoke and TOX:
            yield dgaf.util.install_task("tox")
        else:
            yield dgaf.util.install_task("pytest")

    def post(self):
        if not self.smoke and TOX:
            # can we infer a good tox test
            yield task("test-tox", self.CONTENT + [TOX, False], ..., "tox")
        else:
            yield task("test-pytest", self.CONTENT + [PYPROJECT, False], ..., "pytest")


class Docs(Tasks):
    def prior(self):
        yield dgaf.util.install_task("jupyter_book")

    def post(self):
        yield task(
            "build-html-docs",
            self.CONTENT + [TOC, CONFIG],
            ["build/html"],
            "jb build .",
        )


class Discover(Tasks):
    def prior(self):
        yield task(
            "discover-dependencies",
            self.CONTENT + [SETUPCFG],
            REQUIREMENTS,
            self.discover_dependencies,
        )


class Develop(Tasks):
    def prior(self):
        state = SETUPCFG.load()
        # infer the declarative setup file.
        if hasattr(state, "to_dict"):
            state = state.to_dict()
        yield task("setup.cfg", self.CONTENT, SETUPCFG, self.to_setup_cfg)

        # add __init__ to folders
        yield task(
            "__init__.py",
            " ".join(sorted(map(str, self.DIRECTORIES))),
            self.INITS,
            self.init_directories,
        )

        # create a manifest to define the files to include
        yield task(
            str(MANIFESTIN),
            " ".join(sorted(map(str, self.CONTENT))),
            MANIFESTIN,
            self.create_manifest,
        )
        if self.install:
            if not self.pep517:
                yield task("setup.py", SETUPCFG, SETUPPY, self.to_setup_py)
        elif self.develop:
            yield task("setup.py", SETUPCFG, SETUPPY, self.to_setup_py)

    def post(self):
        yield task(
            "develop-package",
            SETUPPY,
            File("build/pip.freeze"),
            [
                lambda: File("build/pip.freeze").unlink()
                if File("build/pip.freeze")
                else None,
                "pip install -e . --ignore-installed",
                "pip list > build/pip.freeze",
            ],
        )


class Install(Develop):
    def post(self):
        yield task(
            "build-dist",
            self.CONTENT + [SETUPPY, SETUPCFG, README],
            self.DISTS,
            "python setup.py sdist bdist_wheel",
        )
        yield task(
            "install-package",
            self.DISTS,
            File("build/pip.freeze"),
            [
                lambda: File("build/pip.freeze").unlink()
                if File("build/pip.freeze")
                else None,
                f"pip install --no-index --find-links=dist {self.get_name()}",
                "pip list > build/pip.freeze",
            ],
        )


class Poetry(Install):
    ...


class PEP517(Install):
    def prior(self):
        yield task("build-system", SETUPCFG, PYPROJECT, self.setup_cfg_to_pyproject)

    def post(self):
        yield task(
            "build-dist",
            self.CONTENT + [PYPROJECT, SETUPCFG, README],
            self.DISTS,
            "python -m pep517.build .",
        )


class Conda(Tasks):
    def prior(self):
        yield dgaf.util.install_task("ensureconda", actions=["ensureconda"])
        yield task(
            "discover-conda-environment",
            [state["options"], SETUPCFG],
            ENVIRONMENT,
            self.setup_cfg_to_environment_yml,
        )

    def post(self):
        yield task(
            "update-conda",
            ENVIRONMENT,
            ...,
            f"""{
                    self.mamba and "mamba" or "conda"
                } env update -f {ENVIRONMENT}""",
        )


class Pip(Tasks):
    def post(self):
        yield task("update-pip", REQUIREMENTS, ..., f"pip install -r {REQUIREMENTS}")
