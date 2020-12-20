"""qpub.py
q(uick) p(ubishing) is a swiss army knife for configuring projects.

it configures python distributions, linting and formatting, testing
conditions, and documentation.

it is meant for ideas with little content, like gist, but can scale with
large projects that abide community conventions.




"""
__version__ = __import__("datetime").date.today().strftime("%Y.%m.%d")
import os
import pathlib
import typing
import dataclasses

Path = type(pathlib.Path())


class options:
    """options for qpub

    options are passed to doit using environment variables in nox."""

    backend: str = os.environ.get("QPUB_BACKEND", "flit")
    install: bool = os.environ.get("QPUB_INSTALL", False)
    develop: bool = os.environ.get("QPUB_DEVELOP", False)
    conda: bool = os.environ.get("QPUB_CONDA", False)
    pdf: bool = os.environ.get("QPUB_DOCS_PDF", False)
    blog: bool = os.environ.get("QPUB_BLOG", False)
    html: bool = os.environ.get("QPUB_DOCS_HTML", False)
    watch: bool = os.environ.get("QPUB_DOCS_WATCH", False)
    lint: bool = os.environ.get("QPUB_LINT", False)

    @classmethod
    def dump(cls):
        return {f"QPUB_{x.upper()}": getattr(cls, x) for x in cls.__annotations__}


# Files and File Utilities


class File(Path):
    """a supercharged file object that make it is easy to dump and load data.

    the loaders and dumpers edit files in-place, these constraints may not apply to all systems.
    """

    def read(self):
        return self.load()

    def write(self, object):
        self.write_text(self.dump(object))

    def update(self, object):
        return self.write(util.merge(self.read(), object))

    __add__ = update

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


class INI(File):
    """dump and load ini files in place."""

    _suffixes = ".ini", ".cfg"

    def load(self):
        # try:
        #     __import__("configupdater")
        #     callable = util.load_configupdater
        # except ModuleNotFoundError:
        #     callable = util.load_configparser
        try:
            return callable(self.read_text())
        except FileNotFoundError:
            return callable("")

    def dump(self, object):
        return util.dump_config__er(object)


class TOML(File):
    """dump and load toml files in place."""

    _suffixes = (".toml",)

    def load(self):
        try:
            __import__("tomlkit")
            callable = util.load_tomlkit
        except ModuleNotFoundError:
            callable = util.load_toml
        try:
            return callable(self.read_text())
        except FileNotFoundError:
            return callable("")

    def dump(self, object):
        return util.dump_toml(object)


class YML(File):
    """dump and load yml files in place."""

    _suffixes = ".yaml", ".yml"

    def load(self):
        try:
            __import__("ruamel.yaml")
            callable = util.load_ruamel
        except ModuleNotFoundError:
            callable = util.load_yaml
        try:
            return callable(self.read_text())
        except FileNotFoundError:
            return callable("{}")

    def dump(self, object):
        return util.dump_yaml(object)


class Convention(File):
    """a convention indicates explicit or implicit filename and directory conventions.

    the conventions were introduced to separate non-canonical content from canonical configuration files.
    if content and configurations are mixed they doit will experience break with cyclic graphs.
    """


# conventional file names.


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

MANIFEST = Convention("MANIFEST.in")
ENVIRONMENT_YML = Convention("environment.yml")
ENVIRONMENT_YAML = Convention("environment.yaml")
GITHUB = Convention(".github")
WORKFLOWS = GITHUB / "workflows"
CONVENTIONS = [x for x in locals().values() if isinstance(x, Convention)]


# the cli program stops here. there rest work for the tasks
# in the sections below we define tasks to configure distributions.


@dataclasses.dataclass(order=True)
class FileSystem:
    is_vcs = False
    dir: str = "."
    all: list = dataclasses.field(default_factory=list)
    submodules: list = dataclasses.field(default_factory=list)
    files: list = dataclasses.field(default_factory=list)
    directories: list = dataclasses.field(default_factory=list)
    top_level: list = dataclasses.field(default_factory=list)
    suffixes: list = dataclasses.field(default_factory=list)

    def __post_init__(self):
        self.dir = Path(self.dir)
        if not self.all:
            self.all = list(x for x in File(self.dir).rglob("*") if not x.is_dir())

        self.files = [
            File(x)
            for x in self.all
            if x not in self.submodules and x not in CONVENTIONS
        ]
        # the files in the submodules.
        [
            self.files.extend(
                x
                for x in map(File, __import__("git").Git(x).ls_files().splitlines())
                if x not in CONVENTIONS
            )
            for x in self.submodules
        ]
        self.exclude = self.get_exclude_paths()
        self.content = [x for x in self.files if x not in self.exclude]
        # the non-conventional directories containing content
        self.directories = sorted(
            set(
                x.parent.relative_to(self.dir)
                for x in self.content
                if x.parent not in CONVENTIONS
                if x.parent.absolute() != self.dir.absolute()
            )
        )

        # the top level directories
        self.top_level = sorted(
            map(File, set(x.parts[0] for x in self.directories if x.parts))
        )

        self.suffixes = sorted(set(x.suffix for x in self.files))

    def get_author(self):
        return ""

    def get_email(self):
        return ""

    def get_url(self):
        return ""

    def get_exclude_patterns(self):
        """get the excluded by the canonical python.gitignore file.

        this method can construct a per project gitignore file rather than
        included the world.
        """
        return list(sorted(set(dict(self._iter_exclude()).values())))

    def get_exclude_paths(self):
        """get the excluded by the canonical python.gitignore file.

        this method can construct a per project gitignore file rather than
        included the world.
        """
        return list(sorted(dict(self._iter_exclude(self.files))))

    def _iter_exclude(self, files=None):
        import itertools

        docs = self.dir / DOCS
        for x in files or itertools.chain(
            self.dir.iterdir(), docs.iterdir() if docs.exists() else tuple()
        ):
            exclude = self.get_exclude_by(x.relative_to(self.dir))
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

        for pattern in (
            Path(__file__).parent / "Python.gitignore"
        ).read_text().splitlines() + ".vscode _build".split():
            if bool(pattern):
                match = __import__("pathspec").patterns.GitWildMatchPattern(
                    pattern.rstrip("/")
                )
                if match.include:
                    self.gitignore_patterns[pattern.rstrip("/")] = match

    def get_module_name_from_files(self):
        test_files = self.get_test_files()
        canonical, tests, pythonic, named, post = [], [], [], [], []
        post_pattern = __import__("re").compile("[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}-(.*)")
        for x in sorted(self.content):
            if x.suffix in {".md", ".py", ".rst", ".ipynb"}:
                if x.stem.lower() in {"readme", "index"}:
                    canonical += [x]
                elif x in test_files:
                    tests += [x]
                elif post_pattern.match(x.stem):
                    post += [x]
                else:
                    try:
                        __import__("ast").parse(x.stem)
                        pythonic += [x]
                    except SyntaxError:
                        named += [x]
        if pythonic:
            return pythonic[0].stem

        if post:
            "fix the name"
        if canonical:
            "figure out a name some how"

    def get_module_name_from_directories(self):
        if len(self.top_level) == 1:
            return self.top_level[0].stem

    def get_module_name(self):
        if self.top_level:
            return self.get_module_name_from_directories()
        return self.get_module_name_from_files()

    def get_test_files(self, default=True):
        """list the test like files. we'll access their dependencies separately ."""
        if default:
            return [x for x in self.content if x.stem.startswith("test_")]
        items = util.collect_test_files(self.path)
        return items

    def get_untracked_files(self):
        return []


@dataclasses.dataclass(order=True)
class Git(FileSystem):
    is_vcs = True
    repo: "git.Repo" = None

    def __post_init__(self):
        self.all = list(
            map(File, __import__("git").Git(self.dir).ls_files().splitlines())
        )
        self.repo = __import__("git").Repo(self.dir)
        super().__post_init__()

    def get_author(self):
        return self.repo.commit().author.name

    def get_email(self):
        return self.repo.commit().author.email

    def get_url(self):
        try:
            return self.repo.remote("origin").url
        except ValueError:
            return ""

    def get_untracked_files(self):
        return self.repo.untracked_files


@dataclasses.dataclass(order=True)
class Project:
    """the Project class provides a consistent interface for inferring project features from
    the content of directories and git repositories.

    """

    dir: object = dataclasses.field(default_factory=Path)
    fs: FileSystem = dataclasses.field(default_factory=dict)

    @property
    def path(self):
        return File(self.dir)

    def __truediv__(self, object):
        return self.path / object

    def __post_init__(self):
        """post initialize globs of content relative the git repository."""

        self.fs = ((self / GIT).exists() and Git or FileSystem)(self.dir)
        # self.add()

    @property
    def files(self):
        return self.fs.content

    @property
    def suffixes(self):
        return self.fs.suffixes

    def add(self, *object):
        """add an object to the project, add will provide heuristics for different objects much the same way `poetry add` does."""
        if self.fs.is_vcs:
            for object in object:
                if isinstance(object, (str, Path)):
                    self.fs.repo.index.add([str(object)])

            self.fs.repo.index.commit("dgaf added files.")
            self.fs.__post_init__()

    def get_name(self):
        """get the name of the project distribution.

        this method is used to infer the project names for setuptools, flit, or poetry. projects make
        have the form of:
        - flat repository with no directories.
        - a project with a src directory.
        - folders with custom names

        what is the canonical name for a collection of folders?
        - exclude private names.
        """
        # we know default pytest settings so we shouldnt have to invoke pytest to find tests if the folder is flat.
        return self.fs.get_module_name()

    def get_exclude(self):
        return self.fs.get_exclude_patterns()

    def get_version(self):
        """determine a version for the project, if there is no version defer to calver.

        it would be good to support semver, calver, and agever (for blogs).
        """
        # use the flit convention to get the version.
        return __import__("datetime").date.today().strftime("%Y.%m.%d")

    def get_description(self):
        """get from the docstring of the project. raise an error if it doesn't exist."""
        # use the flit convention to get the description.
        # flit already does this.
        # get the description from a markdown cell if it exists.
        # get it from the docstring
        return ""

    def get_description_file(self):
        """get the description file for a project. it looks like readme or index something."""
        for file in self.fs.files:
            if file.stem.lower() in {"readme", "index"}:
                return file

    def get_description_content_type():
        """get the description file for a project. it looks like readme or index something."""
        file = self.get_description_file()
        return {".md": "text/markdown", ".rst": "text/x-rst"}.get(
            file and file.suffix.lower() or None, "text/plain"
        )

    def get_long_description(self):
        file = self.get_description_file()
        return f"file: {file}" if file else ""

    def get_author(self):
        """get the author name from the git revision history.

        we can only infer an author if a commit is generated."""
        return self.fs.get_author()

    def get_email(self):
        """get the author name from the git revision history.

        we can only infer an author if a commit is generated."""
        return self.fs.get_email()

    def get_requires_from_files(self, files):
        """list imports discovered from the files."""
        return list(set(util.import_to_pip(util.merged_imports(files))))

    def get_requires_from_requirements_txt(self):
        """get any hardcoded dependencies in requirements.txt."""
        if (self / REQUIREMENTS_TXT).exists():
            known = [
                x
                for x in REQUIREMENTS_TXT.read_text().splitlines()
                if not x.lstrip().startswith("#") and x.strip()
            ]
            return list(
                __import__("packaging.requirements")
                .requirements.Requirement.parseString(x)
                .name
                for x in known
            )

        return []

    def get_requires(self):
        """get the requirements for the project.

        use heuristics that investigate a few places where requirements may be specified.

        the expectation is that pip requirements might be pinned in a requirements file
        or anaconda environment file.
        """
        known = self.get_requires_from_requirements_txt()

        known.append(self.get_name())
        return sorted(
            [
                package
                for package in self.get_requires_from_files(
                    [self / x for x in self.files if x not in self.get_test_files()]
                )
                if package.lower() not in known and package[0].isalpha()
            ]
        )

    def get_test_requires(self):
        """test requires live in test and docs folders."""

        requires = ["pytest", "pytest-sugar"]
        if ".ipynb" in self.suffixes:
            requires += ["nbval", "importnb"]
        requires += self.get_requires_from_files(
            self / x for x in self.get_test_files()
        )
        return [x for x in requires if x not in [self.get_name()]]

    def get_doc_requires(self):
        """test requires live in test and docs folders."""

        # infer the sphinx extensions needed because we miss this often.
        if CONF in self.files:
            "infer the dependencies from conf.py."
        return ["jupyter-book"]

        return requires

    def get_url(self):
        """get the url(s) for the project from the git history."""
        return self.fs.get_url()

    def get_classifiers(self):
        """some classifiers can probably be inferred."""
        return []

    def get_license(self):
        """should be a trove classifier"""
        # import trove_classifiers

        # infer the trove framework
        # make a gui for adding the right classifiers.

        return ""

    def get_keywords(self):
        return ""

    def get_python_version(self):
        import sys

        return f">={sys.version_info.major}.{sys.version_info.minor}"

    def get_test_files(self, default=True):
        """list the test like files. we'll access their dependencies separately ."""
        if default:
            return [x for x in self.files if x.stem.startswith("test_")]
        items = util.collect_test_files(self.path)
        return items

    def get_doc_files(self):
        """get the files that correspond to documentation.


        * docs folder may have different depdencies for execution.
        * is the readme docs? it is docs and test i think.
        """
        return [x for x in self.files if x.parts[0] == "docs"]

    def get_entry_points(self):
        """combine entrypoints from all files.

        is there a convention for entry points?
        can we infer anything?
        """
        # read entry points from setup.cfg
        # read entry points from pyproject.toml
        ep = {}
        return ep
        if (self / SETUP_CFG).exists():
            data = (self / SETUP_CFG).load()
            if "options.entry_points" in data:
                for k, v in data["options.entry_points"].items():
                    ep = merge(
                        ep,
                        {
                            k: dict(x.split("=", 1))
                            for x in v.value.splitlines()
                            if x.strip()
                        },
                    )
        if (self / PYPROJECT_TOML).exists():
            data = (self / PYPROJECT_TOML).load()
            ep = merge(
                ep,
                dict(
                    console_scripts=data.get("tool", {})
                    .get("flit", {})
                    .get("scripts", {})
                ),
            )
            ep = merge(
                ep, data.get("tool", {}).get("flit", {}).get("entrypoints", {})
            )  # other ep
            ep = merge(
                ep,
                dict(
                    console_scripts=data.get("tool", {})
                    .get("poetry", {})
                    .get("scripts", {})
                ),
            )  # poetry console_scripts
            ep = merge(ep, data.get("tool", {}).get("poetry", {}).get("plugins", {}))

        return ep

    def to_pre_commit(self):
        """from the suffixes in the content, fill out the precommit based on our opinions."""
        precommit = self / PRECOMMITCONFIG_YML
        data = precommit.load() or {}
        if "repos" not in data:
            data["repos"] = []

        for suffix in [None] + list(set(x.suffix for x in self.files)):
            if suffix in util.LINT_DEFAULTS:
                for kind in util.LINT_DEFAULTS[suffix]:
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

        precommit.dump(data)

    def to_flit(self):
        description_file = self.get_description_file()
        url = self.get_url()
        name = self.get_name()
        version = self.get_version()
        (self / PYPROJECT_TOML) + dict(
            tool=dict(
                flit=dict(
                    metadata=dict(
                        module=name,
                        author=self.get_author(),
                        maintainer=self.get_author(),
                        requires=self.get_requires(),
                        classifiers=self.get_classifiers(),
                        keywords=self.get_keywords(),
                        license=self.get_license(),
                        urls={},
                        **{
                            "author-email": self.get_email(),
                            "maintainer-email": self.get_email(),
                            "requires-extra": {
                                "test": self.get_test_requires(),
                                "docs": self.get_doc_requires(),
                            },
                            "requires-python": self.get_python_version(),
                            **(
                                description_file
                                and {"description-file": str(description_file)}
                                or {}
                            ),
                            **(url and {"home-page": url} or {}),
                        },
                    ),
                    scripts={},
                    sdist={},
                    entrypoints=self.get_entry_points(),
                ),
                pytest=dict(ini_options=self.to_pytest_config()),
            ),
            **{
                "build-system": {
                    "requires": "flit_core>=2,<4".split(),
                    "build-backend": "flit_core.buildapi",
                }
            },
        )
        adds = [self / PYPROJECT_TOML]
        # the case where isnt any python source.
        if not ((self / name).exists() or (self / name).with_suffix(".py").exists()):
            (self / name).with_suffix(".py").write_text(
                f"""
"{name}"
__version__ = "{version}"
with __import__("importnb").Notebook():
    from {name} import *\n"""
            )
            adds += [
                (self / name).with_suffix(".py"),
                (self / name).with_suffix(".ipynb"),
            ]
            if self.fs.is_vcs and self.fs.get_untracked_files():
                (self / GITIGNORE).open("a")
                (self / GITIGNORE).write_text(
                    "\n".join(["", *map(str, self.fs.get_untracked_files())])
                )
                adds += [self / GITIGNORE]
        self.add(*adds)

    def to_toc_yml(self):
        """

        book > part > chapter > section

        there are two conventions for jupyter book:
        1. using sections
        2. using files

        """
        (self / TOC).dump(self.get_sections())

    def get_sections(self):
        collated = __import__("collections").defaultdict(list)
        # collated[None] is the top level
        collated[(None,)].append(self.get_description_file())

        if collated[(None,)][0] is None:
            collated.pop()

        if not collated[(None,)]:
            try:
                collated[(None,)].append(next(self.get_posix_names()))
            except StopIteration:
                ...

        for file in sorted(self.files):
            if file not in sum(collated.values(), []):
                collated[file.parent.parts].append(file)

        sections = [
            dict(file=str(collated.pop((None,)).pop(0).with_suffix("")), sections=[])
        ]
        # a rough first pass.
        for part in sorted(collated):
            if part == (None,):
                continue
            for file in collated[part]:
                if file.suffix.lower() in {".md", ".ipynb", ".rst", ".txt"}:
                    sections[0]["sections"].append(dict(file=str(file.with_suffix(""))))

        return sections

    def get_section_files(self):
        ...

    def to_config_yml(self):
        """configure the book project once and never again.

        https://jupyterbook.org/customize/config.html

        """
        (self / CONFIG).dump(
            dict(
                title=self.get_name(),
                author=self.get_author(),
                copyright="2020",
                logo="",
                only_build_toc_files=True,
                repository=dict(url=self.get_url(), path_to_book="", branch="gh-pages"),
                execute=dict(execute_notebooks="off"),
                exclude_patterns=list(map(str, self.get_exclude())),
                html=dict(
                    favico="",
                    use_edit_page_button=True,
                    use_repository_button=True,
                    use_issues_button=False,
                    extra_navbar="",
                    extra_footer="",
                    google_analytics_id="",
                    home_page_in_navbar=True,
                    baseurl="",
                    comments=dict(hypothesis=False, utterances=False),
                    launch_buttons=dict(
                        notebook_interface="lab",
                        binderhub_url="https://mybinder.org",
                        jupyterhub_url="",
                        thebe=True,
                        colab_url="",
                    ),
                ),
                sphinx=dict(
                    extra_extensions=[],
                    local_extensions=[],
                    config=dict(bibtex_bibfiles=[]),
                ),
            )
        )

    def to_setup_py(self):
        (self / SETUP_PY).write_text("""__import__("setuptools").setup()""")

    def to_setuptools(self):
        requires = self.get_requires()
        test_requires = self.get_test_requires()
        docs_requires = self.get_doc_requires()
        (self / SETUP_CFG) + dict(
            metadata=dict(
                name=self.get_name(),
                version=self.get_version(),
                url=self.get_url(),
                author=self.get_author(),
                author_email=self.get_email(),
                maintainer=self.get_author(),
                maintainer_email=self.get_email(),
                classifiers=self.get_classifiers(),
                license=self.get_license(),
                description=self.get_description(),
                long_description=self.get_long_description(),
                keywords=self.get_keywords(),
                platforms=[],
                requires=requires,
            ),
            options=dict(
                zip_safe=False,
                python_requires=self.get_python_version(),
                scripts=[],
                setup_requires=[],
                install_requires=requires,
                # extras_require={"test": test_requires, "docs": docs_requires},
            ),
        )

    def to_poetry(self):
        ...

    def to_pytest_config(self):
        return dict(
            addopts="-s",
            norecursedirs=" ".join(map(str, self.get_exclude())),
            minversion="6.2",
        )

    def to_gitignore(self):
        (self / GITIGNORE).write_text("\n".join(map(str, self.get_exclude())))

    def to_manifest(self):
        (self / MANIFEST).write_text(" ".join(map(str, ["include"] + self.files)))

    def to_github_action(self):
        """create a github actions to publish dgaf actionss"""

    def to_readthedocs(self):
        """configure a read the docs deployment with dgaf."""

    def to_requirements(self):
        """write a requirements file."""
        (self / REQUIREMENTS_TXT).update

    def to_conda_environment(self):
        """export a conda environment file."""


# do it tasks.


try:
    doit = __import__("doit")
    project = Project()
except ModuleNotFoundError:
    doit = None


def task_manifest():
    return dict(
        actions=[project.to_manifest],
        targets=[project.path / MANIFEST],
        uptodate=[doit.tools.config_changed(" ".join(map(str, project.files)))],
    )


def task_gitignore():
    return dict(
        actions=[project.to_gitignore],
        targets=[project.path / GITIGNORE],
        uptodate=[doit.tools.config_changed(" ".join(map(str, project.files)))],
    )


def task_lint():
    """produce the configuration files for linting and formatting the distribution."""
    return dict(
        actions=[project.to_pre_commit],
        targets=[project.path / PRECOMMITCONFIG_YML],
        uptodate=[doit.tools.config_changed(" ".join(map(str, project.suffixes)))],
    )


def task_python():
    """produce the configuration files for a python distribution."""
    return dict(
        file_dep=[x for x in project.files if x in {".py", ".ipynb"}],
        actions=[project.to_flit],
        task_dep=["manifest"],
        targets=[project.path / PYPROJECT_TOML],
    )


def task_setup_py():
    """produce the configuration files for a python distribution."""
    return dict(
        actions=[project.to_setup_py],
        targets=[project / SETUP_PY],
        uptodate=[(project / SETUP_PY).exists()],
    )


def task_setuptools():
    """produce the configuration files for a python distribution."""
    return dict(
        file_dep=[x for x in project.files if x in {".py", ".ipynb"}],
        actions=[project.to_setuptools],
        task_dep=["manifest"],
        targets=[project / SETUP_CFG],
    )


def task_blog():
    """produce the configuration files for a blog."""
    return dict(actions=[])


def task_docs():
    """produce the configuration files for the documentation."""
    return dict(
        actions=[project.to_toc_yml, project.to_config_yml],
        targets=[project / TOC, project / CONFIG],
        uptodate=[doit.tools.config_changed(" ".join(map(str, project.files)))],
    )


def task_html():
    """produce the configuration files for the documentation."""
    return dict(
        file_dep=[project / TOC, project / CONFIG] + project.files,
        actions=[
            f"jupyter-book build {project.path}  --path-output docs --toc docs/_toc.yml --config docs/_config.yml"
        ],
        targets=[project.path / DOCS / "_build/html"],
        watch=project.files,
    )


# utilities functions


class util:

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
                repo="https://github.com/psf/black",
                rev="19.3b0",
                hooks=[dict(id="black")],
            ),
            dict(
                repo="https://github.com/life4/flakehell",
                rev="v.0.7.0",
                hooks=[dict(id="flakehell")],
            ),
        ],
    }

    LINT_DEFAULTS[".yaml"] = LINT_DEFAULTS[".yml"]

    def rough_source(nb):
        """extract a rough version of the source in notebook to infer files from"""

        if isinstance(nb, str):
            nb = __import__("json").loads(nb)

        return "\n".join(
            __import__("textwrap").dedent("".join(x["source"]))
            for x in nb.get("cells", [])
            if x["cell_type"] == "code"
        )

    async def infer(file):
        """infer imports from different kinds of files."""
        async with __import__("aiofiles").open(file, "r") as f:
            if file.suffix not in {".py", ".ipynb", ".md", ".rst"}:
                return file, {}
            source = await f.read()
            if file.suffix == ".ipynb":
                source = util.rough_source(source)
            try:
                return (
                    file,
                    __import__("depfinder").main.get_imported_libs(source).describe(),
                )
            except SyntaxError:
                return file, {}

    async def infer_files(files):
        return dict(
            await __import__("asyncio").gather(
                *(util.infer(file) for file in map(Path, files))
            )
        )

    def gather_imports(files):
        """"""
        if "depfinder" not in __import__("sys").modules:
            yaml = __import__("yaml")

            dir = Path(__import__("appdirs").user_data_dir("qpub"))
            __import__("requests_cache").install_cache(str(dir / "qpub"))
            dir.mkdir(parents=True, exist_ok=True)
            if not hasattr(yaml, "CSafeLoader"):
                yaml.CSafeLoader = yaml.SafeLoader
            __import__("depfinder")

            __import__("requests_cache").uninstall_cache()
        return dict(__import__("asyncio").run(util.infer_files(files)))

    def merge(*args):
        if not args:
            return {}
        if len(args) == 1:
            return args[0]
        a, b, *args = args
        if args:
            b = __import__("functools").reduce(util.merge, (b, *args))
        if hasattr(a, "items"):
            for k, v in a.items():
                if k in b:
                    a[k] = util.merge(v, b[k])
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

    def merged_imports(files):
        results = util.merge(*util.gather_imports(files).values())
        return sorted(
            set(
                list(results.get("required", []))
                + list(results.get("questionable", []))
            )
        )

    def import_to_pip(list):
        global IMPORT_TO_PIP
        if not IMPORT_TO_PIP:
            IMPORT_TO_PIP = {
                x["import_name"]: x["pypi_name"]
                for x in __import__("depfinder").utils.mapping_list
            }
        return [IMPORT_TO_PIP.get(x, x) for x in list]

    def pypi_to_conda(list):
        global PIP_TO_CONDA
        if not PIP_TO_CONDA:
            PIP_TO_CONDA = {
                x["import_name"]: x["conda_name"]
                for x in __import__("depfinder").utils.mapping_list
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

    def load_configparser(str):
        object = __import__("configparser").ConfigParser(default_section=None)
        object.read_string(str)
        return util.expand_cfg(object)

    def load_configupdater(str):
        object = __import__("configupdater").ConfigUpdater()
        object.read_string(str)
        return util.expand_cfg(object)

    @ensure_trailing_eol
    def dump_config__er(object):
        next = __import__("io").StringIO()
        object = util.compact_cfg(object)
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
                    value = __import__("textwrap").dedent(value).splitlines()[1:]
                object[main][key] = value
        return object

    def compact_cfg(object):
        for main, section in object.items():
            for key, value in section.items():
                if isinstance(value, list):
                    value = __import__("textwrap").indent("\n".join(value), " " * 4)
                object[main][key] = value
        return object

    def load_text(str):
        return [x for x in str.splitlines()]

    @ensure_trailing_eol
    def dump_text(object):
        return "\n".join(object)

    def load_toml(str):
        return __import__("toml").loads(str)

    def load_tomlkit(str):
        return __import__("tomlkit").parse(str)

    @ensure_trailing_eol
    def dump_toml(object):
        try:
            tomlkit = __import__("tomlkit")
            if isinstance(object, tomlkit.toml_document.TOMLDocument):
                return tomlkit.dumps(object)
        except ModuleNotFoundError:
            pass
        return __import__("toml").dumps(object)

    def load_yaml(str):
        return __import__("yaml").safe_load(str)

    def load_ruamel(str):
        object = __import__("ruamel.yaml").yaml.YAML()
        return object.load(str)

    @ensure_trailing_eol
    def dump_yaml(object):
        try:
            ruamel = __import__("ruamel.yaml").yaml
            if isinstance(object, ruamel.YAML):
                next = __import__("io").StringIO()
                object.dump(next)
                return next.getvalue()
        except ModuleNotFoundError:
            pass
        return __import__("yaml").safe_dump(object)

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


IMPORT_TO_PIP = None
PIP_TO_CONDA = None
