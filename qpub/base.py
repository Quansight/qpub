"""base.py

the base classes for `qpub`
"""
import git, dataclasses
from .files import *
from . import util


@dataclasses.dataclass(order=True)
class Project:
    """the Project class provides a consistent interface for inferring project features from
    the content of directories and git repositories.

    """

    repo: git.Repo = dataclasses.field(default_factory=git.Repo)
    data: dict = dataclasses.field(default_factory=dict)

    def add(self, *object):
        """add an object to the project, add will provide heuristics for different objects much the same way `poetry add` does."""
        for object in object:
            if isinstance(object, (str, Path)):
                self.repo.index.add([str(object)])

        # the submodules in the project.
        self.submodules = [File(x) for x in self.repo.submodules]

        # the files in the project.
        self.files = [
            File(x)
            for x in map(File, git.Git(self.repo.working_dir).ls_files().splitlines())
            if x not in self.submodules
            and x not in self.submodules
            and x not in CONVENTIONS
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
        self.directories = list(
            set(x.parent for x in self.files if x.parent not in CONVENTIONS)
        )

        # the top level directories
        self.top_level = list(
            map(File, set(x.parts[0] for x in self.directories if x.parts))
        )

        self.suffixes = list(set(x.suffix for x in self.files))

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

        for x in itertools.chain(
            Path(self.repo.working_dir).iterdir(),
            Path(self.repo.working_dir, "docs").iterdir(),
        ):
            exclude = self.get_exclude_by(x.relative_to(self.repo.working_dir))
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
            from .template import gitignore

            self.gitignore_patterns = {}

            for pattern in gitignore.splitlines():
                if bool(pattern):
                    match = pathspec.patterns.GitWildMatchPattern(pattern.rstrip("/"))
                    if match.include:
                        self.gitignore_patterns[pattern.rstrip("/")] = match

    def get_name_from_directory():
        """infer the name of the project from the directories."""

    def get_name_from_src_directory():
        """infer the name of a src directory project."""

    def get_name_from_flat():
        """infer the name of a project from a flat (gist-like) directory."""

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
        if not self.top_level:
            modules = [x for x in self.files if not x.stem.startswith("test_")]
            if len(modules) == 1:
                return modules[0].stem
        if len(self.top_level) == 1:
            if self.top_level[0] == self.repo.working_dir / SRC:
                return  # the name in the src directory.
            return str(self.top_level[0])
        return "tmpname"

    def get_version(self):
        """determine a version for the project, if there is no version defer to calver.

        it would be good to support semver, calver, and agever (for blogs).
        """
        # use the flit convention to get the version.
        return __import__("datetime").date.today().strftime("%Y.%m.%d")

    def get_description(self):
        """get from the docstring of the project. raise an error if it doesn't exist."""
        # use the flit convention to get the description.
        return ""

    def get_long_description(self):
        return ""

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
        return list(
            set(
                util.import_to_pip(
                    util.merged_imports(self.repo.working_dir / x for x in files)
                )
            )
        )

    def get_requires_from_requirements_txt(self):
        """get any hardcoded dependencies in requirements.txt."""
        if (self.repo.working_dir / REQUIREMENTS_TXT).exists():
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
            if package.lower() not in known
        ]

    def get_test_requires(self):
        """test requires live in test and docs folders."""

        requires = ["pytest", "pytest-sugar"]
        if ".ipynb" in self.suffixes:
            requires += ["nbval", "importnb"]
        requires += self.get_requires_from_files(
            self.repo.working_dir / x for x in self.get_test_files()
        )
        return requires

    def get_doc_requires(self):
        """test requires live in test and docs folders."""

        # infer the sphinx extensions needed because we miss this often.
        requires = []
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
        prior = tuple(map(str, self.files))
        items = util.collect_test_files(self.repo.working_dir)
        return items

    def get_doc_files(self, default=True):
        """get the files that correspond to documentation.


        * docs folder may have different depdencies for execution.
        * is the readme docs? it is docs and test i think.
        """

        if default:
            return [x for x in self.files if x.stem.startswith("test_")]
        prior = tuple(map(str, self.files))
        items = util.collect_test_files(self.repo.working_dir)
        return items

    def get_entry_points(self):
        """combine entrypoints from all files.

        is there a convention for entry points?
        can we infer anything?
        """
        # read entry points from setup.cfg
        # read entry points from pyproject.toml
        ep = {}
        if (self.repo.working_dir / SETUP_CFG).exists():
            data = (self.repo.working_dir / SETUP_CFG).load()
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
        if (self.repo.working_dir / PYPROJECT_TOML).exists():
            data = (self.repo.working_dir / PYPROJECT_TOML).load()
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


class PyProject(Project):
    def load(self):
        self.data = (self.repo.working_dir / PYPROJECT_TOML).load()
