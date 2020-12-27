"""qpub.py
q(uick) p(ubishing) configures python distribution and documentaton tools.

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
import dataclasses
import itertools
from . import util
from .exceptions import *
from .util import Path, File, Convention


class options:
    """options for qpub

    options are passed to doit using environment variables in nox."""

    python: str = os.environ.get("QPUB_PYTHON", "infer")
    conda: bool = os.environ.get("QPUB_CONDA", False)
    generate_types: bool = os.environ.get("QPUB_GENERATE_TYPES", False)
    docs: str = os.environ.get("QPUB_GENERATE_TYPES", "infer")
    pdf: bool = os.environ.get("QPUB_DOCS_PDF", False)
    doit: bool = os.environ.get("QPUB_DOIt", False)
    watch: bool = os.environ.get("QPUB_DOCS_WATCH", False)
    serve: bool = os.environ.get("QPUB_SERVE", False)

    @classmethod
    def dump(cls):
        return {f"QPUB_{x.upper()}": str(getattr(cls, x)) for x in cls.__annotations__}


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

MANIFEST = Convention("MANIFEST.in")
ENVIRONMENT_YML = Convention("environment.yml")
ENVIRONMENT_YAML = Convention("environment.yaml")
GITHUB = Convention(".github")
WORKFLOWS = GITHUB / "workflows"
CONVENTIONS = [x for x in locals().values() if isinstance(x, Convention)]

BUILDSYSTEM = "build-system"


# the cli program stops here. there rest work for the tasks
# in the sections below we define tasks to configure distributions.


@dataclasses.dataclass(order=True)
class FileSystem:
    is_vcs = False
    dir: str = "."
    all: list = dataclasses.field(default_factory=list, repr=False)
    submodules: list = dataclasses.field(default_factory=list, repr=False)
    files: list = dataclasses.field(default_factory=list)
    directories: list = dataclasses.field(default_factory=list, repr=False)
    top_level: list = dataclasses.field(default_factory=list)
    suffixes: list = dataclasses.field(default_factory=list)

    def __post_init__(self):
        self.dir = Path(self.dir)

        if not self.all:
            docs = File(self.dir, "docs")
            build = docs / "_build"
            interest = list(
                itertools.chain(
                    File(self.dir).iterdir(),
                    (build.iterdir() if build.exists() else tuple()),
                )
            )
            self.exclude = dict(self._iter_exclude(interest))
            self.all = []
            for file in interest:
                if file.is_dir():
                    if file not in self.exclude:
                        self.all += [
                            x for x in file.rglob("*") if not self.get_exclude_by(x)
                        ]

                else:
                    if (file not in self.exclude) and (file.parent not in self.exclude):
                        self.all += [file]
        self.conventions = [File(x) for x in self.all if x in CONVENTIONS]
        self.files = [
            File(x)
            for x in self.all
            if x not in self.submodules and x not in self.conventions
        ]
        self.conventions = []
        # the files in the submodules.
        [
            self.files.extend(
                x
                for x in map(File, __import__("git").Git(x).ls_files().splitlines())
                if x not in CONVENTIONS
            )
            for x in self.submodules
        ]

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
            self.dir.iterdir(), (docs.iterdir() if docs.exists() else tuple())
        ):
            if x.is_dir():
                x /= "tmp"

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
        for file in (
            Path(__file__).parent / "Python.gitignore",
            Path(__file__).parent / "Nikola.gitignore",
            Path(__file__).parent / "JupyterNotebooks.gitignore",
        ):
            for pattern in (
                file.read_text().splitlines()
                + ".local .vscode _build .gitignore".split()
            ):
                if bool(pattern):
                    match = __import__("pathspec").patterns.GitWildMatchPattern(pattern)
                    if match.include:
                        self.gitignore_patterns[pattern] = match

    def get_module_name_from_files(self):
        test_files = self.get_test_files()
        canonical, tests, pythonic, named, post = [], [], [], [], []

        for x in sorted(self.content):
            if x.stem.startswith(("_", ".")):
                """preceeding underscores shield the naming"""
                continue
            if x.suffix in {".md", ".py", ".rst", ".ipynb"}:
                if x.stem.lower() in {"readme", "index"}:
                    canonical += [x]
                elif x in test_files:
                    tests += [x]
                elif util.post_pattern.match(x.stem):
                    post += [x]
                else:
                    try:
                        __import__("ast").parse(x.stem)
                        pythonic += [x]
                    except SyntaxError:
                        named += [x]

        if len(pythonic) > 1:
            stems = []
            print(pythonic)
            pythonic = [
                stems.append(file.stem) or file
                for file in pythonic
                if file.stem not in stems
            ]

        if len(set(pythonic)) == 1:
            return list(set(pythonic))[0].stem, pythonic[0]
        elif pythonic:
            name = self.get_name_from_config()
            if name is None:
                raise ExtraMetadataRequired(
                    "dgaf cannot infer names from multiple files. explicitly define a project name."
                )
            return name, None

        if len(post) == 1:
            post = post[0].stem
            year, month, day, name = post.split("-", 3)
            return name.replace(*"-_"), post[0]
        elif post:
            raise ExtraMetadataRequired(
                "dgaf cannot infer names from multiple posts. make a top level python project or explicitly name the project."
            )

        if canonical:
            canonical = " ".join(canonical)
            raise ExtraMetadataRequired(
                f"dgaf cannot infer canonical names (eg. {canonical}. explicitly define a name or make a python project."
            )

    def get_name_from_config(self):
        return None

    def get_module_name_from_directories(self):
        if SRC in self.top_level:
            return self.get_module_name_from_src_directories()
        if len(self.top_level) == 1:
            return self.top_level[0].stem
        raise ExtraMetadataRequired(
            f"dgaf cannont infer from multiple directories. explicitly define a project name."
        )

    def get_module_name_from_src_directories(self):
        dirs, scripts = [], []
        for file in (self.dir / SRC).iterdir():
            if file.stem.startswith("_"):
                continue
            if file.is_dir():
                dirs.append(file)
            elif file.is_file():
                scripts.append(file)
        if dirs:
            if len(dirs) == 1:
                return dirs[0].stem
            raise ExtraMetadataRequired("can't infer the name from the src project")
        if scripts:
            if len(scripts) == 1:
                return scripts[0].stem
            raise ExtraMetadataRequired("can't infer the name from the src project")
        raise ExtraMetadataRequired("can't infer the name from the src project")

    def get_module_name(self):
        if self.top_level:
            return self.get_module_name_from_directories()
        return self.get_module_name_from_files()[0]

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
        self.exclude = dict(self._iter_exclude(self.all))
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
        # there are a bunch of version convention we can look for bumpversion, semver, rever
        # if the name is a post name then infer the version from there
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
        requires = []
        if options.docs == "jb":
            requires += ["jupyter-book"]

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
        return []

    def get_python_version(self):
        import sys

        return f"{sys.version_info.major}.{sys.version_info.minor}"

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

    def serialize(self, infer=False):
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
        )

        if infer:
            data.update(
                requires=self.get_requires(),
                test_requires=self.get_test_requires(),
                docs_requires=self.get_doc_requires(),
            )

        return data

    def as_flit(self):
        return __import__("jsone").render(
            __import__("json").loads(
                (Path(__file__).parent / "templates" / "flit.json").read_text()
            ),
            self.serialize(True),
        )

    def to_flit(self):
        data = self.as_flit()
        data = util.merge(
            self.as_pytest(),
            {BUILDSYSTEM: data.pop(BUILDSYSTEM)},
            (self / PYPROJECT_TOML).load(),
            data,
        )
        (self / PYPROJECT_TOML).write(data)
        name = data["tool"]["flit"]["metadata"]["module"]
        version = self.get_version()
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

    def to_toc_yml(self):
        """

        book > part > chapter > section

        there are two conventions for jupyter book:
        1. using sections
        2. using files

        """
        (self / TOC).write(self.get_sections())

    def get_sections(self):
        collated = __import__("collections").defaultdict(list)
        # collated[None] is the top level
        collated[(None,)].append(self.get_description_file())

        # if there no description file then pop back
        if collated[(None,)][0] is None:
            collated[(None,)].pop()

        # populate collated top level with the canonical file.
        if not collated[(None,)]:
            try:
                collated[(None,)].append(self.fs.get_module_name_from_files()[1])
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

    def as_config(self):
        return __import__("jsone").render(
            __import__("json").loads(
                (Path(__file__).parent / "templates" / "_config.json").read_text()
            ),
            self.serialize(),
        )

    def to_config_yml(self):
        """configure the book project once and never again.

        https://jupyterbook.org/customize/config.html

        """
        (self / CONFIG).write(self.as_config())

    def to_setup_py(self):
        (self / SETUP_PY).write_text("""__import__("setuptools").setup()""")

    def as_setuptools(self):
        return __import__("jsone").render(
            __import__("json").loads(
                (Path(__file__).parent / "templates" / "setuptools.json").read_text()
            ),
            self.serialize(True),
        )

    def to_setuptools(self):
        data = self.as_setuptools()
        data = util.merge((self / SETUP_CFG).load(), data)
        (self / SETUP_CFG).write(data)

    def as_poetry(self):
        return __import__("jsone").render(
            __import__("json").loads(
                (Path(__file__).parent / "templates" / "poetry.json").read_text()
            ),
            self.serialize(),
        )

    def as_pytest(self):
        return __import__("jsone").render(
            __import__("json").loads(
                (Path(__file__).parent / "templates" / "pytest.json").read_text()
            ),
            self.serialize(),
        )

    def to_poetry(self):
        """configuration for poetry

        https://python-poetry.org/docs/pyproject/"""

        data = self.as_poetry()
        data = util.merge(
            self.as_pytest(),
            {BUILDSYSTEM: data.pop(BUILDSYSTEM)},
            (self / PYPROJECT_TOML).load(),
            data,
        )
        (self / PYPROJECT_TOML).write(data)

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

    def to_doit(self):
        """make a dodo.py file"""

    def to_nox(self):
        """make a noxfile.py file"""

    def to_readthedocs(self):
        """https://docs.readthedocs.io/en/stable/config-file/v2.html"""


# ███████╗██╗███╗   ██╗
# ██╔════╝██║████╗  ██║
# █████╗  ██║██╔██╗ ██║
# ██╔══╝  ██║██║╚██╗██║
# ██║     ██║██║ ╚████║
# ╚═╝     ╚═╝╚═╝  ╚═══╝
