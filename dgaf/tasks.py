import dataclasses
from dgaf.base import Post
from dgaf.base import *
from dgaf.util import task

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


class Precommit(Post):
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


class Test(Post):
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


class Docs(Post):

    # https://jupyterbook.org/customize/toc.html
    def prior(self):
        yield dgaf.util.install_task("jupyter_book")

    def post(self):
        yield task(
            "build-html-docs",
            self.CONTENT + [TOC, CONFIG],
            ["build/html"],
            "jb build .",
        )


class Discover(Post):
    def prior(self):
        yield task(
            "discover-dependencies",
            self.CONTENT + [SETUPCFG],
            REQUIREMENTS,
            self.discover_dependencies,
        )


class Develop(Post):
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
                (doit.tools.create_folder, ["build"]),
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


class Conda(Post):
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


class Pip(Post):
    def post(self):
        yield task("update-pip", REQUIREMENTS, ..., f"pip install -r {REQUIREMENTS}")
