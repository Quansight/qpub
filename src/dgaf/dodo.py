# dodo.py
import aiofiles
import ast
import asyncio
import contextlib
import dataclasses
import datetime
import flit
import functools
import git
import io
import itertools
import json
import os
import packaging.requirements
import pathlib
import pathspec
import re
import shutil
import sys
import textwrap
import typing

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

print(os.getcwd())
import doit


class Reporter(doit.reporter.ConsoleReporter):
    def execute_task(self, task):
        self.outstream.write("MyReporter --> %s\n" % task.title())


DOIT_CONFIG = dict(verbosity=2, reporter=Reporter)


Path = type(pathlib.Path())
post_pattern = re.compile("[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}-(.*)")


def task_docs():
    """configure the documentation"""
    docs = project / DOCS
    backend = project.docs_backend()
    # basically we wanna combine a bunch of shit

    if backend == "mkdocs":
        return dict(
            file_dep=project.all_files(),
            actions=[(doit.tools.create_folder, [docs]), project.to(Mkdocs).add],
            targets=[project / MKDOCS],
        )

    return dict(
        file_dep=project.all_files(),
        actions=[(doit.tools.create_folder, [docs]), project.to(JupyterBook).add],
        targets=[project / CONFIG, project / TOC],
    )


def task_lint():
    """configure formatters and linters"""
    return dict(
        file_dep=project.all_files(),
        actions=[project.to(Lint).add],
        targets=[project / PRECOMMITCONFIG_YML],
    )


def task_python():
    """configure the python project"""
    targets = [project / PYPROJECT_TOML]
    files = project.all_files()
    backend = project.python_backend()
    task_dep = []
    if not any(x for x in files if x.suffix == ".py"):
        notebooks = [x for x in files if x.suffix == ".ipynb"]

        if notebooks:
            task_dep += ["jupytext"]

    if backend == "setuptools":
        targets += [project / SETUP_CFG]
        actions = [project.to(Setuptools).add]
    elif backend == "flit":
        actions = [project.to(Flit).add]
    elif backend == "poetry":
        requires = " ".join(project.get_requires())
        actions = [project.to(Poetry).add, f"poetry add --lock {requires}"]
    return dict(file_dep=files, actions=actions, targets=targets, task_dep=task_dep)


def task_build():
    return dict(
        file_dep=[project / PYPROJECT_TOML],
        actions=["python -m pep517.build ."],
        targets=[project.to_whl(), project.to_sdist()],
    )


def task_setup_py():
    actions = []
    if not SETUP_PY.exists():
        actions += [
            lambda: SETUP_PY.write_text("""__import__("setuptools").setup()\n""")
            and None
        ]
    return dict(file_dep=[SETUP_CFG], actions=actions, targets=[SETUP_PY])


def task_requirements():
    """configure the requirements.txt for the project"""
    return dict(actions=[project.to(Pip).add], targets=[project / REQUIREMENTS_TXT])


def task_conda():
    """configure a conda environment for the distribution"""

    def shuffle_conda():
        import doit

        file = project / ENVIRONMENT_YAML
        env = file.load()
        c, p = [], []
        for dep in env.get("dependencies", []):
            if isinstance(dep, str):
                c += [dep]
            elif isinstance(dep, dict):
                p = dep.pop("pip", [])
        if c:
            action = doit.tools.CmdAction(
                f"""conda install --dry-run -cconda-forge {" ".join(c)}"""
            )
            if action.err:
                for package in packages_from_conda_not_found(action.err.strip()):
                    p.append(c.pop(c.index(package)))
                if p:
                    if "pip" not in c:
                        c += ["pip", dict(pip=p)]

                file.write(dict(dependencies=c))

    return dict(
        actions=[project.to(Conda).add, shuffle_conda],
        targets=[project / ENVIRONMENT_YAML],
    )


def task_gitignore():
    """create a gitignore for the distribution"""
    project = Gitignore()
    return dict(file_dep=project.all_files(), actions=[], targets=[project / GITIGNORE])


def task_ci():
    """configure a ci workflow for test and release a project"""
    return dict(actions=[project.to(Actions).add], targets=[project / BUILDTESTRELEASE])


def task_readthedocs():
    """configure for the distribution for readthedocs"""
    return dict(actions=[project.to(Readthedocs).add], targets=[project / READTHEDOCS])


def task_jupyter_book():
    """build the documentation with jupyter book"""
    docs = project / "docs"
    return dict(
        file_dep=[project / TOC, project / CONFIG],
        actions=[
            "jb build --path-output docs --toc docs/_toc.yml --config docs/_config.yml ."
        ],
        targets=[BUILD / "html"],
        task_dep=["docs"],
        uptodate=[
            doit.tools.config_changed(" ".join(sorted(map(str, project.all_files()))))
        ],
    )


def task_uml():
    """generate a uml diagram of the project with pyreverse."""
    return dict(
        file_dep=project.all_files(),
        actions=[f"pyreverse pyreverse -o png -k {project.get_name()}"],
        targets=[project.path / "classes.png", project.path / "packages.png"],
    )


def task_mkdocs():
    """build the documentation with mkdocs"""
    return dict(file_dep=[MKDOCS], actions=["mkdocs build"], targets=[BUILD / "mkdocs"])


def task_blog():
    """build a blog site with nikola"""
    return dict(file_dep=[CONF], actions=["nikola build"], targets=[BUILD / "nikola"])


def task_pdf():
    """build a pdf version of the documentation"""
    return dict(actions=[])


def task_jupytext():
    actions = []
    if not installed("jupytext"):
        actions += ["pip install jupytext"]
    notebooks = [str(x) for x in project.all_files() if x.suffix == ".ipynb"]
    return dict(
        actions=actions
        + [f"""jupytext --set-formats ipynb,py:percent {" ".join(notebooks)}"""]
    )


class options:
    """options for qpub

    options are passed to doit using environment variables in nox."""

    __annotations__ = {}
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
    mamba: bool = os.environ.get("QPUB_MAMBA", True)
    cache: str = Path(os.environ.get("QPUB_CACHE", Path(__file__).parent / "_data"))
    dev: bool = os.environ.get("QPUB_DEV", True)
    pip_only: bool = os.environ.get("QPUB_PIP", False)
    install: bool = os.environ.get("QPUB_INSTALL", True)
    install_backend: bool = os.environ.get(
        "QPUB_INSTALL_BACKEND",
        (
            "mamba"
            if shutil.which("mamba")
            else "conda"
            if shutil.which("conda")
            else "pip"
        ),
    )

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
            if (self.dir / GIT).exists():
                self.repo = git.Repo(self.dir / GIT)
        if not self.exclude:
            import pathspec

            self.exclude = pathspec.PathSpec.from_lines(
                pathspec.patterns.GitWildMatchPattern,
                self.get_exclude_patterns() + [".git"],
            )
        if (
            self.docs
            or self.chapters
            or self.conventions
            or self.hidden
            or self.modules
            or self.pages
            or self.other
        ):
            return
        contents = (
            self.repo
            and list(map(File, git.Git(self.dir).ls_files().splitlines()))
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
            elif local in CONVENTIONS:
                self.conventions += [file]
            elif local.stem.startswith((".",)):
                self.hidden += [file]
            elif file.is_dir():
                if self.exclude.match_file(str(local / ".tmp")):
                    ...
                else:
                    self.chapters += [file]
                continue
            elif local.stem.startswith(("_",)):
                if local.stem.endswith("_"):
                    self.modules += [file]
                else:
                    self.hidden += [file]
            elif self.exclude.match_file(str(local)):
                continue
            elif file.suffix not in {".ipynb", ".md", ".rst", ".py"}:
                self.other += [file]
            elif file.stem.lower() in {"readme", "index"}:
                self.index = file
            elif post_pattern.match(file.stem):
                self.posts += [file]
            elif is_pythonic(file.stem):
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
            yield from sorted(
                set(
                    itertools.chain(
                        self.tests,
                        self.docs.files(tests=True) if self.docs else [],
                        *(x.files(tests=True) for x in self._chapters if x),
                    )
                )
            )

        for chapter in self._chapters:
            yield from chapter.files(
                content=content,
                posts=posts,
                docs=docs,
                tests=tests,
                conventions=conventions,
                other=other,
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


def cached(callable):
    @functools.wraps(callable)
    def main(self, *args, **kwargs):
        data = self._cache = getattr(self, "_cache", {})
        key = self.dir, callable.__name__
        if (key in data) and (data[key] is not None):
            return data[key]
        data[key] = callable(self, *args, **kwargs)
        return data[key]

    return main


@contextlib.contextmanager
def cd(object):
    next = os.getcwd()
    os.chdir(object)
    yield
    os.chdir(next)


class Project(Chapter):
    def reset(self):
        self._flit_module = None

    def add(self, *tasks):
        with cd(self.dir):
            main(list(tasks))

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
            names = sorted(
                set(str(x.relative_to(x.parent).with_suffix("")) for x in self.modules)
            )
            if len(names) == 1:
                return names[0]
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

        if self.tests:
            if len(self.tests) == 1:
                return self.tests[0].stem
        raise BaseException

    def get_description(self):
        """get from the docstring of the project. raise an error if it doesn't exist."""

        # look in modules/chapters to see if we can flit this project.
        if self.is_flit():
            import flit

            with contextlib.redirect_stderr(io.StringIO()):
                try:
                    return flit.common.get_info_from_module(self._flit_module).pop(
                        "summary"
                    )
                except:
                    ...

        if self.src:
            return self.src.get_description()

        return ""

    def get_version(self):
        """determine a version for the project, if there is no version defer to calver.

        it would be good to support semver, calver, and agever (for blogs).
        """
        # use the flit convention to get the version.
        # there are a bunch of version convention we can look for bumpversion, semver, rever
        # if the name is a post name then infer the version from there

        version = None
        if self.is_flit():
            with contextlib.redirect_stderr(io.StringIO()):
                try:
                    version = flit.common.get_info_from_module(self._flit_module).pop(
                        "version"
                    )
                except:
                    pass
        if version is None:
            if self.src:
                version = self.src.get_version()
            else:
                version = datetime.date.today().strftime("%Y.%m.%d")
        return normalize_version(version)

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
            file = where_template(file)
            for pattern in (
                file.read_text().splitlines()
                + ".local .vscode _build .gitignore".split()
            ):
                if bool(pattern):
                    match = pathspec.patterns.GitWildMatchPattern(pattern)
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
        return list(set(import_to_pypi(merged_imports(files))))

    def get_requires_from_requirements_txt(self):
        """get any hardcoded dependencies in requirements.txt."""
        if (self / REQUIREMENTS_TXT).exists():
            known = [
                x
                for x in REQUIREMENTS_TXT.read_text().splitlines()
                if not x.lstrip().startswith("#") and x.strip()
            ]
            return list(packaging.requirements.Requirement(x).name for x in known)

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

        import flit

        if self._flit_module is None:
            try:
                self._flit_module = flit.common.Module(self.get_name(), self.dir)
                return True
            except ValueError as e:
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
            files=sorted(map(str, self.all_files())),
            dirs=list(set(str(x.parent) for x in self.all_files() if x)),
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
            merge(
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
        return templated_file("flit.json", self.metadata(True))


class Pytest(PyProject):
    def dump(self):
        return templated_file("pytest.json", self.metadata())


class FlakeHell(PyProject):
    def dump(self):
        return {}


class Poetry(PyProject):
    def dump(self):
        return templated_file("poetry.json", self.metadata())


class Setuptools(PyProject):
    def dump_cfg(self):
        cfg = "setuptools_cfg.json"
        return templated_file(cfg, self.metadata(True))

    def dump_toml(self):
        toml = "setuptools_toml.json"
        return templated_file(toml, {})

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
        return templated_file("mkdocs.json", self.metadata())

    def add(self):
        (self / MKDOCS).write(self.dump())


class JupyterBook(Docs):
    def dump_config(self, recurse=False):
        return templated_file("_config.json", self.metadata())

    def dump_toc(self, recurse=False):
        index = self.index
        if index is None:
            for c in (self, *self._chapters):
                for object in (c.pages, c.posts, c.tests, c.modules):
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
        (self / DOCS).mkdir(exist_ok=True)
        (self / TOC).write(JupyterBook.dump_toc(self, True))
        (self / CONFIG).write(JupyterBook.dump_config(self))


class Readthedocs(Docs):
    def dump(self):
        return templated_file("readthedocs.json", self.metadata())

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


def rough_source(nb):
    """extract a rough version of the source in notebook to infer files from"""

    if isinstance(nb, str):
        nb = json.loads(nb)

    return "\n".join(
        textwrap.dedent("".join(x["source"]))
        for x in nb.get("cells", [])
        if x["cell_type"] == "code"
    )


def _import_depfinder():
    if "depfinder" not in sys.modules:
        import yaml, requests_cache

        dir = Path(__file__).parent
        requests_cache.install_cache(str(options.cache / "requests_cache"))
        dir.mkdir(parents=True, exist_ok=True)
        if not hasattr(yaml, "CSafeLoader"):
            yaml.CSafeLoader = yaml.SafeLoader
        import depfinder

        requests_cache.uninstall_cache()
    return __import__("depfinder")


async def infer(file):
    """infer imports from different kinds of files."""
    depfinder = _import_depfinder()

    async with aiofiles.open(file, "r") as f:
        if file.suffix not in {".py", ".ipynb", ".md", ".rst"}:
            return file, {}
        source = await f.read()
        if file.suffix == ".ipynb":
            source = rough_source(source)
        try:
            return (file, depfinder.main.get_imported_libs(source).describe())
        except SyntaxError:
            return file, {}


async def infer_files(files):
    return dict(await asyncio.gather(*(infer(file) for file in map(Path, set(files)))))


def gather_imports(files):
    """"""

    object = infer_files(files)
    try:
        return dict(asyncio.run(object))
    except RuntimeError:
        __import__("nest_asyncio").apply()
        return dict(asyncio.run(object))


def merged_imports(files):
    results = merge(*gather_imports(files).values())
    return sorted(
        set(list(results.get("required", [])) + list(results.get("questionable", [])))
    )


def merge(*args):
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


def import_to_pypi(list):
    global IMPORT_TO_PIP
    if not IMPORT_TO_PIP:
        depfinder = _import_depfinder()
        IMPORT_TO_PIP = {
            x["import_name"]: x["pypi_name"] for x in depfinder.utils.mapping_list
        }
    return [IMPORT_TO_PIP.get(x, x) for x in list if x not in ["src"]]


def pypi_to_conda(list):
    global PIP_TO_CONDA

    if not PIP_TO_CONDA:
        depfinder = _import_depfinder()
        PIP_TO_CONDA = {
            x["import_name"]: x["conda_name"] for x in depfinder.utils.mapping_list
        }
    return [PIP_TO_CONDA.get(x, x) for x in list]


# file loader loader/dumper functions


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

    if isinstance(object, ruamel.YAML):
        next = io.StringIO()
        object.dump(next)
        return next.getvalue()
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


IMPORT_TO_PIP = None
PIP_TO_CONDA = None


def is_pythonic(object):

    object = pathlib.Path(object)
    try:
        ast.parse(object.stem)
    except SyntaxError:
        return False
    return "-" not in object.stem


def normalize_version(object):
    import packaging.requirements

    with contextlib.redirect_stdout(io.StringIO()):
        return str(packaging.version.Version(object))


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


def packages_from_conda_not_found(out):
    packages = []
    if out.startswith("PackagesNotFoundError"):
        lines = out.splitlines()[1:]
        for line in lines:
            strip = line.strip()
            if strip.startswith("-"):
                packages += [strip.lstrip("-").lstrip()]
            elif strip:
                break
    return packages


def installed(str):
    try:
        importlib.metadata.distribution(str)
        return True
    finally:
        return False


class NoIndex(BaseException):
    ...


# # ███████╗██╗███╗   ██╗
# # ██╔════╝██║████╗  ██║
# # █████╗  ██║██╔██╗ ██║
# # ██╔══╝  ██║██║╚██╗██║
# # ██║     ██║██║ ╚████║
# # ╚═╝     ╚═╝╚═╝  ╚═══╝


def main(argv=None, raises=False):
    global project
    project = Project()
    if argv is None:
        argv = sys.argv[1:]

    if isinstance(argv, str):
        argv = argv.split()

    main = doit.doit_cmd.DoitMain(doit.cmd_base.ModuleTaskLoader(globals()))

    code = main.run(argv)
    if raises:
        sys.exit(code)


def run_in_doit():
    return sys.argv[0].endswith("bin/doit")


if __name__ == "__main__":
    main(None, True)
elif run_in_doit():
    project = Project()
