import dataclasses
from .base import Distribution, File
from .files import *
from .util import task
from . import util
import importlib
import functools
import doit

_qpub_nox = File(__file__).parent / NOX


class Precommit(Distribution):
    def to_pre_commit_config(self):
        """from the suffixes in the content, fill out the precommit based on our opinions."""
        data = PRECOMMITCONFIG.load()
        if "repos" not in data:
            data["repos"] = []

        for suffix in [None] + list(set(x.suffix for x in self.FILES)):
            if suffix in Precommit.LINT_DEFAULTS:
                for kind in Precommit.LINT_DEFAULTS[suffix]:
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

    def prior(self):
        yield task(
            "infer-pre-commit",
            self.CONTENT + [" ".join(sorted(self.SUFFIXES))],
            PRECOMMITCONFIG,
            functools.partial(Precommit.to_pre_commit_config, self),
        )

    def post(self):
        yield task("format-lint", [False], ..., f"nox -f {_qpub_nox} -s lint")

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


class Test(Distribution):
    def post(self):
        if not self.smoke and TOX:
            # can we infer a good tox test
            yield task("test-tox", self.CONTENT + [TOX, False], ..., "tox")
        else:
            yield task("test-pytest", self.CONTENT + [PYPROJECT, False], ..., "pytest")


class Docs(Distribution):
    def post(self):
        yield task(
            "build-html-docs",
            self.CONTENT + [TOC, CONFIG],
            ["build/html"],
            "jb build .",
        )


class Discover(Distribution):
    """discover dependencies for a distribution.

    these tasks can be used to bootstrap an environment or as a safety net when testing.

    """

    discover: bool = True

    def prior(self):
        yield task(
            "discover-dependencies",
            self.CONTENT + [SETUPCFG],
            REQUIREMENTS,
            functools.partial(Discover.discover_dependencies, self),
        )

    def discover_dependencies(self):
        pkg_resources = __import__(
            "pkg_resources"
        )  # do this so depfinder doesn't find me

        prior = []
        for line in REQUIREMENTS.read_text().splitlines() if REQUIREMENTS else []:
            try:
                prior.append(pkg_resources.Requirement(line).name.lower())
            except pkg_resources.extern.packaging.requirements.InvalidRequirement:
                ...

        found = [
            x
            for x in util.import_to_pip(util.merged_imports(self.CONTENT))
            if x.lower() not in prior
        ]
        if found:
            with REQUIREMENTS.open("a") as file:
                file.write("\n" + "\n".join(found))


class Develop(Distribution):
    """Populate the configuration files to develop a package."""

    def create_manifest(self):
        MANIFESTIN.touch()

    def init_directories(self):
        for init in self.INITS:
            if init == SRC:
                continue
            if not init:
                init.touch()

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
        config = Develop.to_metadata_options(self)

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

        SETUPCFG.dump(data)

    def to_metadata_options(self):
        import setuptools

        UNKNOWN = "UNKNOWN"
        data = dict()
        object = data["metadata"] = dict()
        if self.distribution.get_name() == UNKNOWN:
            object["name"] = Develop.get_name(self)
        if self.distribution.get_version() == "0.0.0":
            object["version"] = __import__("datetime").date.today().strftime("%Y.%m.%d")
        if self.distribution.get_url() == UNKNOWN:
            object["url"] = self.REPO.remote("origin").url
            if object["url"].endswith(".git"):
                object["url"] = object["url"][: -len(".git")]

        if self.distribution.get_download_url() == UNKNOWN:
            # populate this for a release
            pass

        if self.distribution.get_author() == UNKNOWN:
            object["author"] = self.REPO.commit().author.name

        if self.distribution.get_author_email() == UNKNOWN:
            object["author_email"] = self.REPO.commit().author.email

        if self.distribution.get_maintainer() == UNKNOWN:
            pass

        if self.distribution.get_maintainer_email() == UNKNOWN:
            pass

        if not self.distribution.get_classifiers():
            # import trove_classifiers
            # https://github.com/pypa/trove-classifiers/
            pass

        if self.distribution.get_license() == UNKNOWN:
            # There has to be a service for these.
            pass

        if self.distribution.get_description() == UNKNOWN:
            object["description"] = ""

        if self.distribution.get_long_description() == UNKNOWN:
            # metadata['long_description_content_type']
            object["long_description"] = f"""file: {README}"""

        if not self.distribution.get_keywords():
            pass

        if self.distribution.get_platforms() == [UNKNOWN]:
            pass

        if not self.distribution.get_provides():
            # https://www.python.org/dev/peps/pep-0314/
            pass

        if not self.distribution.get_requires():
            # cant have versions?
            pass

        if not self.distribution.get_obsoletes():
            pass

        object = data["options"] = dict()
        if self.distribution.zip_safe is None:
            object["zip_safe"] = False

        if not self.distribution.setup_requires:
            pass
        if not self.distribution.install_requires:
            object["install_requires"] = list(
                x
                for x in (REQUIREMENTS.read_text().splitlines() if REQUIREMENTS else [])
                if x.strip()
            )
        if not self.distribution.extras_require:
            data["options.extras_require"] = dict(test=[], docs=[])
            pass

        if not self.distribution.python_requires:
            pass
        if not self.distribution.entry_points:
            data["options.entry_points"] = {}

        if self.distribution.scripts is None:
            pass

        if self.distribution.eager_resources is None:
            pass

        if not self.distribution.dependency_links:
            pass
        if not self.distribution.tests_require:
            pass
        if self.distribution.include_package_data is None:
            object["include_package_data"] = True

        if self.distribution.packages is None:
            object["packages"] = self.packages

        if not self.distribution.package_dir:
            if SRC.exists():
                object["package_dir"] = ["=src"]
            pass

        if not self.distribution.package_data:
            pass

        if self.distribution.exclude_package_data is None:
            pass

        if self.distribution.namespace_packages is None:
            pass

        if not self.distribution.py_modules:
            pass

        if not self.distribution.data_files:
            pass

        return data

    def to_setup_py(self):
        # https://setuptools.readthedocs.io/en/latest/userguide/declarative_config.html#configuring-setup-using-setup-cfg-files
        SETUPPY.write_text("""__import__("setuptools").setup()""".strip())

    def dev_dependencies(self):
        """find the development depdencies we need."""
        deps = []
        if self.smoke:
            deps += ["pytest"]
        elif TOX:
            deps += ["tox"]
        elif NOX:
            deps += ["nox"]
        if self.pep517:
            deps += ["pep517"]
        else:
            deps += ["setuptools", "wheel"]

        if self.lint:
            deps += ["pre_commit"]

        if self.poetry and self.develop:
            # don't need this on an install
            deps += ["poetry"]

        if self.conda:
            deps += ["ensureconda"]

        if self.mamba:
            deps += ["mamba"]

        if self.docs:
            deps += ["jupyter_book"]
        return deps

    def prior(self):
        state = getattr(SETUPCFG.load(), "_sections", {})

        # add __init__ to folders
        yield task(
            "__init__.py",
            " ".join(sorted(map(str, self.DIRECTORIES))),
            self.INITS,
            functools.partial(Develop.init_directories, self),
        )

        # create a manifest to define the files to include
        yield task(
            str(MANIFESTIN),
            " ".join(sorted(map(str, self.CONTENT))),
            MANIFESTIN,
            functools.partial(Develop.create_manifest, self),
        )

        # infer the declarative setup file.
        # this gets run on install, but may not necessary
        yield task(
            "setup.cfg",
            self.CONTENT,
            SETUPCFG,
            functools.partial(Develop.to_setup_cfg, self),
        )

        setuppy_task = task(
            "setup.py", SETUPCFG, SETUPPY, functools.partial(Develop.to_setup_py, self)
        )
        if self.install:
            if not self.pep517:
                yield setuppy_task
        elif self.develop:
            yield setuppy_task

        dev = Develop.dev_dependencies(self)

        def write_dev():
            REQUIREMENTSDEV.write_text("\n".join(dev))

        yield task(
            "dev-deps",
            self.CONTENT + [" ".join(sorted(dev))],
            File("requirements-dev.txt"),
            write_dev,
        )
        yield task(
            "install-dev-deps",
            [REQUIREMENTSDEV] + list(map(bool, map(importlib.util.find_spec, dev))),
            ...,
            "pip install -r requirements-dev.txt",
        )

    def post(self):
        data = getattr(SETUPCFG.load(), "_sections", {})
        yield task(
            "develop-package",
            [data],
            ...,
            [
                (doit.tools.create_folder, ["build"]),
                lambda: File("build/pip.freeze").unlink()
                if File("build/pip.freeze")
                else None,
                "pip install -e . --ignore-installed",
            ],
        )


class Install(Develop):
    def post(self):
        if self.pep517:
            yield task(
                "build-system", SETUPCFG, PYPROJECT, Develop.setup_cfg_to_pyproject
            )
            yield task(
                "build-dist",
                self.CONTENT + [PYPROJECT, SETUPCFG, README],
                self.DISTS,
                "python -m pep517.build .",
            )
        else:
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
                (doit.tools.create_folder, ["build"]),
                lambda: File("build/pip.freeze").unlink()
                if File("build/pip.freeze")
                else None,
                f"pip install --no-index --find-links=dist {self.get_name()}",
                "pip list > build/pip.freeze",
            ],
        )


class Poetry(Install):
    ...


class Conda(Distribution):
    def prior(self):
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


class Pip(Distribution):
    def post(self):
        yield task("update-pip", REQUIREMENTS, ..., f"pip install -r {REQUIREMENTS}")
