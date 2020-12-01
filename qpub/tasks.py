import dataclasses
from qpub.base import Distribution
from qpub.base import *
from qpub.util import task
import importlib
import functools


class Precommit(Distribution):
    def to_pre_commit_config(self):
        """from the suffixes in the content, fill out the precommit based on our opinions."""
        data = PRECOMMITCONFIG.load()
        if "repos" not in data:
            data["repos"] = []

        for suffix in [None] + list(set(x.suffix for x in self.FILES)):
            if suffix in Precommit`.LINT_DEFAULTS:
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
        yield task(
            "install-pre-commit-hooks",
            [PRECOMMITCONFIG, PRECOMMITCONFIG.load()],
            ...,
            "pre-commit install-hooks",
        )

    def post(self):
        yield task("format-lint", [False], ..., "python -m pre_commit run --all-files")

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
    def prior(self):
        yield task(
            "discover-dependencies",
            self.CONTENT + [SETUPCFG],
            REQUIREMENTS,
            functools.partial(Discover.discover_dependencies, self),
        )

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

    def discover_dependencies(self):
        import pkg_resources

        prior = []
        for line in REQUIREMENTS.read_text().splitlines() if REQUIREMENTS else []:
            try:
                prior.append(pkg_resources.Requirement(line).name.lower())
            except pkg_resources.extern.packaging.requirements.InvalidRequirement:
                ...

        found = [
            x for x in qpub.util.merged_imports(self.CONTENT) if x.lower() not in prior
        ]
        with REQUIREMENTS.open("a") as file:
            file.write("\n" + "\n".join(found))


class Develop(Distribution):
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
        data = qpub.base.SETUPCFG.load()
        config = qpub.util.to_metadata_options(self)

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

        qpub.base.SETUPCFG.dump(data)

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

    def prior(self):
        state = SETUPCFG.load()
        # infer the declarative setup file.
        if hasattr(state, "to_dict"):
            state = state.to_dict()
        yield task(
            "setup.cfg",
            self.CONTENT,
            SETUPCFG,
            functools.partial(Develop.to_setup_cfg, self),
        )

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

        setuppy_task = task(
            "setup.py", SETUPCFG, SETUPPY, functools.partial(Develop.to_setup_py, self)
        )
        if self.install:
            if not self.pep517:
                yield setuppy_task
        elif self.develop:
            yield setuppy_task

        dev = Discover.dev_dependencies(self)

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
        yield task(
            "develop-package",
            [SETUPCFG, SETUPPY],
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
            yield task("build-system", SETUPCFG, PYPROJECT, self.setup_cfg_to_pyproject)
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
