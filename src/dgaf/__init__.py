"""q(uick) p(ubishing) configures python Project and documentaton tools.

"""
#    ___    ____      _   _    ____
#   / " \ U|  _"\ uU |"|u| |U | __")u
#  | |"| |\| |_) |/ \| |\| | \|  _ \/
# /| |_| |\|  __/    | |_| |  | |_) |
# U \__\_\u|_|      <<\___/   |____/
#    \\//  ||>>_   (__) )(   _|| \\_
#   (_(__)(__)__)      (__) (__) (__)

__version__ = __import__("datetime").date.today().strftime("%Y.%m.%d")
import os
import pathlib
import typing
import re
import io
import dataclasses
import contextlib
import itertools
import importlib
from . import util
from .exceptions import *
from .util import Path, File, Convention, cached

post_pattern = re.compile("^[0-9]{4}-[0-9]{2}-[0-9]{2}")

try:
    doit = __import__("doit")
except ModuleNotFoundError:
    doit = None


class options:
    """options for qpub

    options are passed to doit using environment variables in nox."""

    python: str = os.environ.get("QPUB_PYTHON", "infer")
    conda: bool = os.environ.get("QPUB_CONDA", False)
    tasks: str = os.environ.get("QPUB_TASKS", "").split()
    generate_types: bool = os.environ.get("QPUB_GENERATE_TYPES", False)
    docs: str = os.environ.get("QPUB_GENERATE_TYPES", "infer")
    pdf: bool = os.environ.get("QPUB_DOCS_PDF", False)
    watch: bool = os.environ.get("QPUB_DOCS_WATCH", False)
    serve: bool = os.environ.get("QPUB_SERVE", False)
    binder: bool = os.environ.get("BINDER_URL", False)
    confirm: bool = os.environ.get("QPUB_CONFIRM", False)
    posargs: bool = os.environ.get("QPUB_POSARGS", "").split()
    dgaf: str = os.environ.get("QPUB_ID", "dgaf")
    interactive: bool = os.environ.get("QPUB_INTERACTIVE", False)
    monkeytype: bool = os.environ.get("QPUB_INTERACTIVE", False)

    @classmethod
    def dump(cls):
        return {
            f"QPUB_{x.upper()}": " ".join(x)
            if isinstance(x, list)
            else str(getattr(cls, x))
            for x in cls.__annotations__
        }


# ███████╗██╗██╗     ███████╗     ██████╗ ██████╗ ███╗   ██╗██╗   ██╗███████╗███╗   ██╗████████╗██╗ ██████╗ ███╗   ██╗███████╗
# ██╔════╝██║██║     ██╔════╝    ██╔════╝██╔═══██╗████╗  ██║██║   ██║██╔════╝████╗  ██║╚══██╔══╝██║██╔═══██╗████╗  ██║██╔════╝
# █████╗  ██║██║     █████╗      ██║     ██║   ██║██╔██╗ ██║██║   ██║█████╗  ██╔██╗ ██║   ██║   ██║██║   ██║██╔██╗ ██║███████╗
# ██╔══╝  ██║██║     ██╔══╝      ██║     ██║   ██║██║╚██╗██║╚██╗ ██╔╝██╔══╝  ██║╚██╗██║   ██║   ██║██║   ██║██║╚██╗██║╚════██║
# ██║     ██║███████╗███████╗    ╚██████╗╚██████╔╝██║ ╚████║ ╚████╔╝ ███████╗██║ ╚████║   ██║   ██║╚██████╔╝██║ ╚████║███████║
# ╚═╝     ╚═╝╚══════╝╚══════╝     ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝  ╚═══╝  ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝


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

MANIFEST = Convention("MANIFEST.in")
ENVIRONMENT_YML = Convention("environment.yml")
ENVIRONMENT_YAML = Convention("environment.yaml")
GITHUB = Convention(".github")
WORKFLOWS = GITHUB / "workflows"
BUILDTESTRELEASE = WORKFLOWS / "build_test_release.yml"
READTHEDOCS = Convention(".readthedocs.yml")

CONVENTIONS = [x for x in locals().values() if isinstance(x, Convention)]


BUILDSYSTEM = "build-system"


# the cli program stops here. there rest work for the tasks
# in the sections below we define tasks to configure Project


@dataclasses.dataclass(order=True)
class Chapter:
    dir: pathlib.Path = ""
    index: None = None
    repo: object = None
    parent: object = None
    docs: object = None
    posts: list = dataclasses.field(default_factory=list)
    pages: list = dataclasses.field(default_factory=list)
    modules: list = dataclasses.field(default_factory=list)
    tests: list = dataclasses.field(default_factory=list)
    src: object = None
    chapters: list = dataclasses.field(default_factory=list)
    other: list = dataclasses.field(default_factory=list)
    _chapters: list = dataclasses.field(default_factory=list)
    conventions: list = dataclasses.field(default_factory=list, repr=False)
    hidden: list = dataclasses.field(default_factory=list, repr=False)
    exclude: object = None

    _flit_module = None

    def get_exclude_patterns(self):
        return []

    def __post_init__(self):
        if not isinstance(self.dir, pathlib.Path):
            self.dir = File(self.dir)
        if self.repo is None:
            self.repo = (
                (self.dir / GIT).exists()
                and __import__("git").Repo(self.dir / GIT)
                or None
            )
        if not self.exclude:
            pathspec = __import__("pathspec")
            self.exclude = pathspec.PathSpec.from_lines(
                pathspec.patterns.GitWildMatchPattern,
                self.get_exclude_patterns() + [".git"],
            )
        if not (
            self.docs
            or self.chapters
            or self.conventions
            or self.hidden
            or self.modules
            or self.pages
            or self.other
        ):
            contents = (
                self.repo
                and list(
                    map(File, __import__("git").Git(self.dir).ls_files().splitlines())
                )
                or None
            )

            for parent in contents or []:
                if parent.parent not in contents:
                    contents += [parent.parent]

            for file in self.dir.iterdir():
                local = file.relative_to(self.dir)
                if contents is not None:
                    if local not in contents:
                        continue

                if local in {DOCS}:
                    self.docs = Docs(dir=file, parent=self)
                elif local in {SRC}:
                    self.src = Project(dir=file, parent=self)
                    self.chapters += [x for x in file.iterdir() if x.is_dir()]
                elif local in CONVENTIONS:
                    self.conventions += [file]
                elif local.stem.startswith((".",)):
                    self.hidden += [file]
                elif file.is_dir():
                    if self.exclude.match_file(local / ".tmp"):
                        ...
                    else:
                        self.chapters += [file]
                    continue
                elif local.stem.startswith(("_",)):
                    if local.stem.endswith("_"):
                        self.modules += [file]
                    else:
                        self.hidden += [file]
                elif self.exclude.match_file(local):
                    continue
                elif file.suffix not in {".ipynb", ".md", ".rst", ".py"}:
                    self.other += [file]
                elif file.stem.lower() in {"readme", "index"}:
                    self.index = file
                elif post_pattern.match(file.stem):
                    self.posts += [file]
                elif util.is_pythonic(file.stem):
                    if file.stem.startswith("test_"):
                        self.tests += [file]
                    else:
                        self.modules += [file]
                else:
                    self.pages += [file]

            for k in "chapters posts tests modules pages conventions".split():
                setattr(self, k, sorted(getattr(self, k), reverse=k in {"posts"}))

            self._chapters = list(Chapter(dir=x, parent=self) for x in self.chapters)

    def root(self):
        return self.parent.root() if self.parent else self

    def all_files(self, conventions=False):
        return list(self.files(True, True, True, True, conventions, True))

    def files(
        self,
        content=False,
        posts=False,
        docs=False,
        tests=False,
        conventions=False,
        other=False,
    ):
        if self.index:
            yield self.index
        if posts:
            yield from self.posts
        if docs:
            yield from self.pages
            if self.docs:
                yield from self.docs.files(
                    content=content,
                    posts=posts,
                    docs=docs,
                    tests=tests,
                    conventions=conventions,
                )
        if content:
            yield from self.modules
        if tests:
            yield from self.tests
        for chapter in self._chapters:
            yield from chapter.files(
                content=content,
                posts=posts,
                docs=docs,
                tests=tests,
                conventions=conventions,
            )
        if conventions:
            yield from self.conventions

        if other:
            yield from self.other

    @property
    def path(self):
        return File(self.dir)

    def __truediv__(self, object):
        return self.path / object

    @property
    def suffixes(self):
        return sorted(set(x.suffix for x in self.files(True, True, True, True, True)))

    @classmethod
    def to(self, type):
        return type(
            **{k: v for k, v in vars(self).items() if k in type.__annotations__}
        )


class Project(Chapter):
    @cached
    def get_name(self):
        """get the project name"""

        # get the name of subdirectories if there are any.
        if self.src:
            return self.src.get_name()

        if self.chapters:
            if len(self.chapters) == 1:
                return self.chapters[0].stem

        # get the name of modules if there are any.
        if self.modules:
            if len(self.modules) == 1:
                return self.modules[0].stem
            else:
                raise BaseException

        # look for dated posted
        if self.posts:
            if len(self.posts) == 1:
                return self.posts[0].stem.split("-", 3)[-1].replace(*"-_")

        # look for pages.
        if self.pages:
            if len(self.pages) == 1:
                return self.pages[0].stem
        raise BaseException

    @cached
    def get_description(self):
        """get from the docstring of the project. raise an error if it doesn't exist."""

        # look in modules/chapters to see if we can flit this project.
        if self.is_flit():
            flit = __import__("flit")
            with contextlib.redirect_stderr(io.StringIO()):
                return flit.common.get_info_from_module(self._flit_module).pop(
                    "summary"
                )

        if self.src:
            return self.src.get_description()

        return ""

    @cached
    def get_version(self):
        """determine a version for the project, if there is no version defer to calver.

        it would be good to support semver, calver, and agever (for blogs).
        """
        # use the flit convention to get the version.
        # there are a bunch of version convention we can look for bumpversion, semver, rever
        # if the name is a post name then infer the version from there

        if self.is_flit():
            flit = __import__("flit")
            with contextlib.redirect_stderr(io.StringIO()):
                version = flit.common.get_info_from_module(self._flit_module).pop(
                    "version"
                )

        if self.src:
            version = self.src.get_version()
        else:
            version = __import__("datetime").date.today().strftime("%Y.%m.%d")
        return util.normalize_version(version)

    @cached
    def get_exclude_patterns(self):
        """get the excluded patterns for the current layout"""
        return list(sorted(set(dict(self._iter_exclude()).values())))

    @cached
    def get_exclude_paths(self):
        """get the excluded path by the canonical python.gitignore file."""
        return list(sorted(dict(self._iter_exclude())))

    def _iter_exclude(self, files=None):
        for x in files or itertools.chain(self.dir.iterdir(), (self.dir / BUILD,)):
            if x.is_dir():
                x /= "tmp"

            exclude = self.get_exclude_by(x.relative_to(self.root().dir))
            if exclude:
                yield x, exclude

    def get_exclude_by(self, object):
        """return the path that ignores an object.

        exclusion is based off the canonical python.gitignore specification."""
        if not hasattr(self, "gitignore_patterns"):
            self._init_exclude()

        for k, v in self.gitignore_patterns.items():
            if any(v.match((str(object),))):
                return k
        else:
            return None

    def _init_exclude(self):
        """initialize the path specifications to decide what to omit."""

        self.gitignore_patterns = {}
        import importlib.resources

        for file in (
            "Python.gitignore",
            "Nikola.gitignore",
            "JupyterNotebooks.gitignore",
        ):
            with importlib.resources.path("dgaf.templates", file) as file:
                for pattern in (
                    file.read_text().splitlines()
                    + ".local .vscode _build .gitignore".split()
                ):
                    if bool(pattern):
                        match = __import__("pathspec").patterns.GitWildMatchPattern(
                            pattern
                        )
                        if match.include:
                            self.gitignore_patterns[pattern] = match

    @cached
    def get_author(self):
        if self.repo:
            return self.repo.commit().author.name
        return "dgaf"

    @cached
    def get_email(self):
        if self.repo:
            return self.repo.commit().author.email
        return ""

    @cached
    def get_url(self):
        if self.repo:
            if hasattr(self.repo.remotes, "origin"):
                return self.repo.remotes.origin.url
        return ""

    get_exclude = get_exclude_patterns

    @cached
    def get_classifiers(self):
        """some classifiers can probably be inferred."""
        return []

    @cached
    def get_license(self):
        """should be a trove classifier"""
        # import trove_classifiers

        # infer the trove framework
        # make a gui for adding the right classifiers.
        "I dont know what the right thing is to say here."
        return ""

    @cached
    def get_keywords(self):
        return []

    def get_python_version(self):
        import sys

        return f"{sys.version_info.major}.{sys.version_info.minor}"

    @cached
    def get_test_files(self):
        """list the test like files. we'll access their dependencies separately ."""
        return list(self.files(tests=True))

    @cached
    def get_docs_files(self):
        """list the test like files. we'll access their dependencies separately ."""
        backend = self.docs_backend()
        requires = []
        if backend == "mkdocs":
            requires += ["mkdocs"]
        if backend == "sphinx":
            requires += ["sphinx"]
        if backend == "jb":
            requires += ["jupyter-book"]

        return requires + list(self.files(docs=True))

    def get_untracked_files(self):
        if self.repo:
            self.repo.untracked_files
        return []

    @cached
    def get_description_file(self):
        """get the description file for a project. it looks like readme or index something."""
        if self.index and self.index.stem.lower() in {"readme", "index"}:
            return self.index

    @cached
    def get_description_content_type(self):
        """get the description file for a project. it looks like readme or index something."""
        file = self.get_description_file()
        return {".md": "text/markdown", ".rst": "text/x-rst"}.get(
            file and file.suffix.lower() or None, "text/plain"
        )

    @cached
    def get_long_description(self, expand=False):
        file = self.get_description_file()
        if expand:
            return file.read_text()
        return f"file: {file}" if file else ""

    def get_requires_from_files(self, files):
        """list imports discovered from the files."""
        return list(set(util.import_to_pypi(util.merged_imports(files))))

    def get_requires_from_requirements_txt(self):
        """get any hardcoded dependencies in requirements.txt."""
        if (self / REQUIREMENTS_TXT).exists():
            known = [
                x
                for x in REQUIREMENTS_TXT.read_text().splitlines()
                if not x.lstrip().startswith("#") and x.strip()
            ]
            return list(
                __import__("packaging.requirements").requirements.Requirement(x).name
                for x in known
            )

        return []

    @cached
    def get_requires(self):
        """get the requirements for the project.

        use heuristics that investigate a few places where requirements may be specified.

        the expectation is that pip requirements might be pinned in a requirements file
        or anaconda environment file.
        """
        known = [self.get_name()]
        return sorted(
            [
                package
                for package in self.get_requires_from_files(self.files(content=True))
                if package.lower() not in known and package[0].isalpha()
            ]
        )

    @cached
    def get_test_requires(self):
        """test requires live in test and docs folders."""

        requires = ["pytest", "pytest-sugar"]
        if ".ipynb" in self.suffixes:
            requires += ["nbval", "importnb"]
        requires += self.get_requires_from_files(
            self / x for x in self.get_test_files()
        )
        return [x for x in requires if x not in [self.get_name()]]

    def get_docs_requires(self):
        """test requires live in test and docs folders."""

        # infer the sphinx extensions needed because we miss this often.
        if CONF in self.conventions:
            "infer the dependencies from conf.py."
        requires = []
        backend = self.docs_backend()
        if backend == "jb":
            requires += ["jupyter-book"]
        if backend == "mkdocs":
            requires += ["mkdocs"]

        if backend == "sphinx":
            requires += ["sphinx"]
        if self.docs:
            requires += self.get_requires_from_files(self.docs.files())
        return requires

    def is_flit(self):
        """does the module abide flit conventions:

        1. is the python script or folder with a name
        2. can the description and version be inferred

        """

        flit = __import__("flit")
        if self._flit_module is None:
            try:
                self._flit_module = flit.common.Module(self.get_name(), self.dir)
                return True
            except ValueError:
                return False
        return True

    def is_poetry(self):
        """is the project otherwise a poetry project"""

        return bool(not self.is_flit()) and bool(self.chapters)

    def is_setuptools(self):
        """is the project otherwise a poetry project"""

        return True

    def python_backend(self):
        if options.python == "infer":
            return (
                "flit"
                if self.is_flit()
                else "poetry"
                if self.is_poetry()
                else "setuptools"
            )
        return options.python

    def docs_backend(self):
        if options.docs == "infer":
            return "jb"
        return options.docs

    def metadata(self, infer=False):
        url = self.get_url()
        if url.endswith(".git"):
            url = url[:-4]
        exclude = map(str, self.get_exclude())
        exclude = [x[:-1] if x.endswith("/") else x for x in exclude]

        data = dict(
            name=self.get_name(),
            version=self.get_version(),
            url=url,
            author=self.get_author(),
            email=self.get_email(),
            classifiers=self.get_classifiers(),
            license=self.get_license(),
            description=self.get_description(),
            long_description=str(self.get_description_file()),
            keywords=self.get_keywords(),
            platforms=[],
            python_version=self.get_python_version(),
            exclude=exclude,
            language="en",
            files=list(map(str, self.all_files())),
        )

        if infer:
            data.update(
                requires=self.get_requires(),
                test_requires=self.get_test_requires(),
                docs_requires=self.get_docs_requires(),
            )

        return data

    def to_whl(self):
        return self / DIST / f"{self.get_name()}-{self.get_version()}-py3-none-any.whl"

    def to_sdist(self):
        return self / DIST / f"{self.get_name()}-{self.get_version()}.tar.gz"


class Environment(Project):
    ...


class Conda(Environment):
    def pip_to_conda(self):
        return list(self.get_requires())

    def dump(self):
        return dict(dependencies=self.pip_to_conda(), channels="conda-forge".split())

    def add(self):
        (self / ENVIRONMENT_YAML).write(self.dump())


class Pip(Environment):
    def add(self):
        (self / REQUIREMENTS_TXT).write("\n".join(self.get_requires()))


class Python(Project):
    def add(self):
        backend = self.python_backend()
        (
            Flit if backend == "flit" else Poetry if backend == "poetry" else Setuptools
        ).add(self)


class PyProject(Python):
    def dump(self):
        return {}

    def add(self):
        data = self.dump()
        (self.dir / PYPROJECT_TOML).update(
            util.merge(
                {BUILDSYSTEM: data.pop(BUILDSYSTEM)},
                self.to(FlakeHell).dump(),
                self.to(Pytest).dump(),
                data,
            )
        )


class Flit(PyProject):
    """flit projects are discovered when a python script
    or directory exists with docstring and version."""

    def dump(self):
        return util.templated_file(
            "flit.json",
            self.metadata(True),
        )


class Pytest(PyProject):
    def dump(self):
        return util.templated_file(
            "pytest.json",
            self.metadata(),
        )


class FlakeHell(PyProject):
    def dump(self):
        return {}


class Poetry(PyProject):
    def dump(self):
        return util.templated_file(
            "poetry.json",
            self.metadata(),
        )


class Setuptools(PyProject):
    def dump_cfg(self):
        cfg = "setuptools_cfg.json"
        return util.templated_file(cfg, self.metadata(True))

    def dump_toml(self):
        toml = "setuptools_toml.json"
        return util.templated_file(toml, {})

    def add(self):
        (self / SETUP_CFG).update(self.dump_cfg())
        (self / PYPROJECT_TOML).update(self.dump_toml())


class Gitignore(Project):
    def dump(self):
        project = Project()
        return project.get_exclude()

    def add(self):
        (self / GITIGNORE).update
        self.dump()


class Lint(Project):
    def add(self):
        self.to(Precommit).add()


class Precommit(Lint):
    def dump(self):
        defaults = (File(__file__).parent / "templates" / "precommit.json").load()
        precommit = self / PRECOMMITCONFIG_YML
        data = precommit.load() or {}
        if "repos" not in data:
            data["repos"] = []

        for suffix in ["null"] + self.suffixes:
            if suffix in defaults:
                for kind in defaults[suffix]:
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

        return data

    def add(self):
        (self / PRECOMMITCONFIG_YML).write(self.dump())


class CI(Project):
    def add(self):
        self.to(Actions).add()


class Actions(CI):
    def dump(self):
        return {}

    def add(self):
        (self / BUILDTESTRELEASE).update(self.dump())


class Docs(Project):
    def add(self):
        backend = self.docs_backend()
        return (
            JupyterBook
            if backend == "jb"
            else Mkdocs
            if backend == "mkdocs"
            else Sphinx
        ).add(self)


class Sphinx(Docs):
    def add(self):
        pass


class Mkdocs(Docs):
    def dump(self):
        return util.templated_file(
            "mkdocs.json",
            self.metadata(),
        )

    def add(self):
        (self / MKDOCS).write(self.dump())


class JupyterBook(Docs):
    def dump_config(self, recurse=False):
        return util.templated_file(
            "_config.json",
            self.metadata(),
        )

    def dump_toc(self, recurse=False):
        index = self.index
        if index is None:
            for object in (self.pages, self.posts, self.tests, self.modules):
                if object:
                    index = object[0]
                    break
        if not index:
            raise NoIndex()
        data = dict(file=str(index.with_suffix("")), sections=[])
        for x in itertools.chain(
            self.pages,
            (self.docs,) if self.docs else (),
            self.posts,
            self.tests,
            self.modules,
            self.chapters,
        ):
            if x == index:
                continue
            if self.docs and (x == self.docs):
                try:
                    data["sections"].append(JupyterBook.dump_toc(self.docs, recurse))
                except NoIndex:
                    ...
            elif x in self.chapters:
                try:
                    data["sections"].append(
                        JupyterBook.dump_toc(
                            self._chapters[self.chapters.index(x)], recurse
                        )
                    )
                except NoIndex:
                    ...
            else:
                data["sections"].append(dict(file=str(x.with_suffix(""))))

        return data

    def add(self):
        (self / TOC).write(JupyterBook.dump_toc(self, True))
        (self / CONFIG).write(JupyterBook.dump_config(self))


class Readthedocs(Docs):
    def dump(self):
        return util.templated_file(
            "readthedocs.json",
            self.metadata(),
        )

    def add(self):
        (self / DOCS / READTHEDOCS).write(self.dump())


class Blog(Docs):
    def add(self):
        self.to(Nikola).add()


class Nikola(Blog):
    """we'll have to add metadata to make nikola work."""

    def add(self):
        (self / CONF).write_text("""""")


class Build(PyProject):
    ...


class CondaBuild(Build):
    ...


class Jupytext(Project):
    ...


class Lektor(Docs):
    ...


class Nbdev(Docs):
    ...


class Devto(CI):
    """https://github.com/marketplace/actions/devto-act"""


class Tweet(CI):
    """https://github.com/gr2m/twitter-together/"""


# # ███████╗██╗███╗   ██╗
# # ██╔════╝██║████╗  ██║
# # █████╗  ██║██╔██╗ ██║
# # ██╔══╝  ██║██║╚██╗██║
# # ██║     ██║██║ ╚████║
# # ╚═╝     ╚═╝╚═╝  ╚═══╝
