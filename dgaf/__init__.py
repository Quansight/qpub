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

    def update(self, object):
        if self.suffix in INI._suffixes:
            config = self.load()
            prior = config.to_dict()
            self._merge(config, object)
            if prior != config.to_dict():
                self.dump(config)
        else:
            self.dump(self._merge(self.load() or {}, object))

    @classmethod
    def _flatten(cls, x):
        import textwrap

        if hasattr(x, "items"):
            for k, v in x.items():
                x[k] = cls._flatten(v)
        if isinstance(x, list):
            return "\n" + textwrap.indent("\n".join(x), " " * 4)
        return x

    @classmethod
    def _update(cls, a, b):
        try:
            a.update(b)
        except:
            import configupdater

            a.update(configupdater.ConfigUpdater(b))
        return a

    @classmethod
    def _merge(cls, a, b, *c):
        if hasattr(a, "items"):
            if not a:
                return cls._update(a, b)

            for k, v in a.items():
                if k in b:
                    a[k] = cls._merge(v, b[k])

            for k, v in b.items():
                if k not in a:
                    try:
                        a[k] = v
                    except ValueError:
                        import configupdater

                        a.add_section(k)
                        a[k].update(v)

        if isinstance(a, (set, list, tuple)):
            return list(sorted(set(a).union(b)))
        return a


class INI(File):
    """dump and load ini files in place."""

    _suffixes = ".ini", ".cfg"

    def load(self):
        try:
            object = __import__("configupdater").ConfigUpdater()
        except:
            object = __import__("configparser").ConfigParser()
        try:
            object.read_string(self.read_text())
        except FileNotFoundError:
            object.read_string("")
        return object

    def dump(self, object):
        self.write_text(str(flatten(object)) + "\n")


class TOML(File):
    """dump and load toml files in place."""

    _suffixes = (".toml",)

    def load(self):
        try:
            return __import__("tomlkit").parse(self.read_text())
        except FileNotFoundError:
            return __import__("tomlkit").parse("")

    def dump(self, object):

        self.write_text(__import__("tomlkit").dumps(object) + "\n")


class YML(File):
    """dump and load yml files in place."""

    _suffixes = ".yaml", ".yml"

    def load(self):
        try:
            object = __import__("ruamel.yaml").yaml.YAML()
            try:
                return object.load(self.read_text()) or object.load("{}")
            except FileNotFoundError:
                return object.load("{}")
        except ModuleNotFoundError:
            try:
                return __import__("yaml").safe_load(self.read_text())
            except FileNotFoundError:
                return {}

    def dump(self, object):
        with self.open("w") as file:
            try:
                __import__("ruamel.yaml").yaml.YAML().dump(object, file)
            except ModuleNotFoundError:
                file.write(__import__("yaml").safe_dump(object))


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


import dataclasses
import git


@dataclasses.dataclass(order=True)
class Project:
    """the Project class provides a consistent interface for inferring project features from
    the content of directories and git repositories.

    """

    repo: git.Repo = dataclasses.field(default_factory=Path)
    data: dict = dataclasses.field(default_factory=dict)

    def add(self, *object):
        """add an object to the project, add will provide heuristics for different objects much the same way `poetry add` does."""
        for object in object:
            if isinstance(object, (str, Path)):
                self.repo.index.add([str(object)])

        # the submodules in the project.
        self.submodules = [File(x) for x in self.repo.submodules]

        # the files in the project.
        self.all = list(map(File, git.Git(self.path).ls_files().splitlines()))
        self.files = [
            File(x)
            for x in self.all
            if x not in self.submodules and x not in CONVENTIONS
        ]
        # the files in the submodules.
        [
            self.files.extend(
                x
                for x in map(File, git.Git(x).ls_files().splitlines())
                if x not in CONVENTIONS
            )
            for x in self.submodules
        ]

        # the non-conventional directories containing content
        self.directories = sorted(
            set(x.parent for x in self.files if x.parent not in CONVENTIONS)
        )

        # the top level directories
        self.top_level = sorted(
            map(File, set(x.parts[0] for x in self.directories if x.parts))
        )

        self.suffixes = sorted(set(x.suffix for x in self.files))

    def __post_init__(self):
        """post initialize globs of content relative the git repository."""

        # submodules in the repository
        if isinstance(self.repo, (str, Path)):
            try:
                self.repo = git.Repo(self.repo)
            except git.InvalidGitRepositoryError:
                git.Git(self.repo).init()
                self.repo = git.Repo(self.repo)
        self.add()

    def get_exclude_by(self, object):
        """return the path that ignores an object.

        exclusion is based off the canonical python.gitignore specification."""
        self._init_exclude()
        for k, v in self.gitignore_patterns.items():
            if any(v.match((str(object),))):
                return k
        else:
            return None

    def _iter_exclude(self):
        import itertools

        docs = Path(self.path, "docs")
        for x in itertools.chain(
            Path(self.path).iterdir(), docs.iterdir() if docs.exists() else tuple()
        ):
            exclude = self.get_exclude_by(x.relative_to(self.path))
            if exclude:
                yield exclude

    def get_exclude(self):
        """get the excluded by the canonical python.gitignore file.

        this method can construct a per project gitignore file rather than
        included the world.
        """
        return list(sorted(set(self._iter_exclude())))

    def _init_exclude(self):
        """initialize the path specifications to decide what to omit."""
        if not hasattr(self, "gitignore_patterns"):
            import pathspec

            self.gitignore_patterns = {}

            for pattern in (
                (Path(__file__).parent / "Python.gitignore").read_text().splitlines()
            ):
                if bool(pattern):
                    match = pathspec.patterns.GitWildMatchPattern(pattern.rstrip("/"))
                    if match.include:
                        self.gitignore_patterns[pattern.rstrip("/")] = match

    def get_file_from_directory(self):
        """infer the name of a src directory project."""
        root = self.path
        if SRC in self.top_level:
            root /= SRC
        for dir in root.iterdir():
            if dir not in self.directories:
                continue
            if not dir.stem.lower().isalpha():
                continue
            yield dir

    def get_file_from_flat():
        """infer the name of a project from a flat (gist-like) directory."""
        description_file = self.get_description_file()
        test_files = self.get_test_files()
        for file in self.files:
            if file == description_file:
                continue
            if file in test_files:
                continue

            if file.stem.startswith("_"):
                continue
            if file.suffix in (".rst", ".md", ".py", ".ipynb"):
                yield file

    def get_file_names(self):
        """list the potentional names for a project"""
        if self.top_level:
            yield from self.get_file_from_directory()
        else:
            yield from self.get_file_from_flat()

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
        try:
            return next(self.get_file_names()).stem
        except StopIteration:
            return "welp"

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
        return ""

    def get_description_file(self):
        """get the description file for a project. it looks like readme or index something."""
        for file in self.files:
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
        try:
            return self.repo.commit().author.name
        except:
            # need a commit to know the author.
            return ""

    def get_email(self):
        """get the author name from the git revision history.

        we can only infer an author if a commit is generated."""
        try:
            return self.repo.commit().author.email
        except ValueError:
            # need to make a commit
            return ""

    def get_requires_from_files(self, files):
        """list imports discovered from the files."""
        return list(set(import_to_pip(merged_imports(self.path / x for x in files))))

    def get_requires_from_requirements_txt(self):
        """get any hardcoded dependencies in requirements.txt."""
        if (self.path / REQUIREMENTS_TXT).exists():
            known = [
                x
                for x in REQUIREMENTS_TXT.read_text().splitlines()
                if not x.lstrip().startswith("#") and x.strip()
            ]
            import packaging.requirements

            return list(
                packaging.requirements.Requirement.parseString(x).name for x in known
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
        return [
            package
            for package in self.get_requires_from_files(
                [x for x in self.files if x not in self.get_test_files()]
            )
            if package.lower() not in known and package[0].isalpha()
        ]

    def get_test_requires(self):
        """test requires live in test and docs folders."""

        requires = ["pytest", "pytest-sugar"]
        if ".ipynb" in self.suffixes:
            requires += ["nbval", "importnb"]
        requires += self.get_requires_from_files(
            self.path / x for x in self.get_test_files()
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
        try:
            return self.repo.remote("origin").url
        except:
            # let the user know there is no remote
            return ""

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
        if (self.path / SETUP_CFG).exists():
            data = (self.path / SETUP_CFG).load()
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
        if (self.path / PYPROJECT_TOML).exists():
            data = (self.path / PYPROJECT_TOML).load()
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
        precommit = self.path / PRECOMMITCONFIG_YML
        data = precommit.load() or {}
        if "repos" not in data:
            data["repos"] = []

        for suffix in [None] + list(set(x.suffix for x in self.files)):
            if suffix in Project.LINT_DEFAULTS:
                for kind in Project.LINT_DEFAULTS[suffix]:
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

    @property
    def path(self):
        return File(self.repo.working_dir)

    def to_flit(self):
        description_file = self.get_description_file()
        (self.path / PYPROJECT_TOML).update(
            dict(
                tool=dict(
                    flit=dict(
                        metadata=dict(
                            module=self.get_name(),
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
                                "home-page": self.get_url(),
                                "requires-extra": {
                                    "test": self.get_test_requires(),
                                    "doc": self.get_doc_requires(),
                                },
                                "requires-python": self.get_python_version(),
                                **(
                                    description_file
                                    and {"description-file": str(description_file)}
                                    or {}
                                ),
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
        )

    def to_toc_yml(self):
        """

        book > part > chapter > section

        there are two conventions for jupyter book:
        1. using sections
        2. using files

        """
        (self.path / TOC).dump(self.get_sections())

    def get_sections(self):
        collated = __import__("collections").defaultdict(list)
        # collated[None] is the top level
        collated[(None,)].append(self.get_description_file())

        if collated[(None,)][0] is None:
            collated.pop()

        if not collated[(None,)]:
            try:
                collated[(None,)].append(next(self.get_file_names()))
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
        (self.path / CONFIG).dump(
            dict(
                title=self.get_name(),
                author=self.get_author(),
                copyright="2020",
                logo="",
                only_build_toc_files=True,
                repository=dict(
                    url=self.get_url(),
                    path_to_book="",
                    branch="gh-pages",
                ),
                execute=dict(
                    execute_notebooks="off",
                ),
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
                    comments=dict(
                        hypothesis=False,
                        utterances=False,
                    ),
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

    def to_setuptools(self):
        dict(
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
                extras_require={},
                entry_points={},
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
        (self.path / GITIGNORE).write_text("\n".join(map(self.get_exclude())))

    def to_manifest(self):
        (self.path / MANIFEST).write_text(" ".join(map(str, ["include"] + self.files)))


# do it tasks.

project = Project()


def task_manifest():
    import doit

    return dict(
        actions=[project.to_manifest],
        targets=[project.path / MANIFEST],
        uptodate=[doit.tools.config_changed(" ".join(map(str, project.files)))],
    )


def task_gitignore():
    import doit

    return dict(
        actions=[project.to_gitignore],
        targets=[project.path / GITIGNORE],
        uptodate=[doit.tools.config_changed(" ".join(map(str, project.files)))],
    )


def task_lint():
    """produce the configuration files for linting and formatting the distribution."""
    import doit

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


def task_blog():
    """produce the configuration files for a blog."""
    return dict(actions=[])


def task_docs():
    """produce the configuration files for the documentation."""
    import doit

    return dict(
        actions=[project.to_toc_yml, project.to_config_yml],
        targets=[project.path / TOC, project.path / CONFIG],
        uptodate=[doit.tools.config_changed(" ".join(map(str, project.files)))],
    )


def task_html():
    """produce the configuration files for the documentation."""
    import doit

    return dict(
        file_dep=[project.path / TOC, project.path / CONFIG] + project.files,
        actions=[
            f"jupyter-book build {project.path}  --path-output docs --toc docs/_toc.yml --config docs/_config.yml"
        ],
        targets=[project.path / DOCS / "_build/html"],
        watch=project.files,
    )


# utilities functions


def rough_source(nb):
    """extract a rough version of the source in notebook to infer files from"""
    import json
    import textwrap

    if isinstance(nb, str):
        nb = json.loads(nb)

    return "\n".join(
        textwrap.dedent("".join(x["source"]))
        for x in nb.get("cells", [])
        if x["cell_type"] == "code"
    )


async def infer(file):
    """infer imports from different kinds of files."""
    import json

    import aiofiles
    import depfinder

    async with aiofiles.open(file, "r") as f:
        if file.suffix not in {".py", ".ipynb", ".md", ".rst"}:
            return file, {}
        source = await f.read()
        if file.suffix == ".ipynb":
            source = rough_source(file.read_text())
        try:
            return file, depfinder.main.get_imported_libs(source).describe()
        except SyntaxError:
            return file, {}


async def infer_files(files):
    return dict(
        await __import__("asyncio").gather(
            *(infer(file) for file in map(pathlib.Path, files))
        )
    )


def gather_imports(files: typing.List[Path]) -> typing.List[dict]:
    """"""
    import asyncio
    import sys
    import yaml

    if "depfinder" not in sys.modules:

        dir = Path(__import__("appdirs").user_data_dir("qpub"))
        __import__("requests_cache").install_cache(str(dir / "qpub"))
        dir.mkdir(parents=True, exist_ok=True)
        if not hasattr(yaml, "CSafeLoader"):
            yaml.CSafeLoader = yaml.SafeLoader
        import depfinder

        __import__("requests_cache").uninstall_cache()
    return dict(asyncio.run(infer_files(files)))


def _merge_shallow(a: dict = None, b: dict = None, *c: dict) -> dict:
    """merge the results of dictionaries."""
    if a is None:
        return {}
    a = a or {}
    if b is None:
        return a
    b = __import__("functools").reduce(_merge_shallow, (b, *c)) if c else b
    for k, v in b.items():
        if k not in a:
            a[k] = a.get(k, [])
        if isinstance(a[k], set):
            a[k] = list(a[k])
        for v in v:
            a[k] += [] if v in a[k] else [v]
    return a


def merged_imports(files: typing.List[Path]) -> dict:
    results = _merge_shallow(*gather_imports(files).values())
    return list(results.get("required", [])) + list(results.get("questionable", []))


IMPORT_TO_PIP = None
PIP_TO_CONDA = None


def import_to_pip(list):
    import depfinder

    global IMPORT_TO_PIP
    if not IMPORT_TO_PIP:
        IMPORT_TO_PIP = {
            x["import_name"]: x["pypi_name"] for x in depfinder.utils.mapping_list
        }
    return [IMPORT_TO_PIP.get(x, x) for x in list]


def pypi_to_conda(list):
    import depfinder

    global PIP_TO_CONDA
    if not PIP_TO_CONDA:
        PIP_TO_CONDA = {
            x["import_name"]: x["conda_name"] for x in depfinder.utils.mapping_list
        }
    return [PIP_TO_CONDA.get(x, x) for x in list]
