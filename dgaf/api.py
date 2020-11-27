import dataclasses
import dgaf
import doit
import typer
import pathlib
import textwrap


@dataclasses.dataclass
class Start(dgaf.base.Project):
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
    def get_name(self):
        
    def discover_dependencies(self):
        data = dgaf.base.File("setup.cfg").load()

        for x in "metadata options".split():
            if x not in data:
                data.add_section(x)

        options = data["options"]
        if "install_requires" not in options:
            options["install_requires"] = """"""
        options["install_requires"] = (
            ""  # str(options["install_requires"])
            + "\n"
            + textwrap.indent("\n".join(dgaf.converters.to_deps()), " " * 4)
        )

        dgaf.base.File("setup.cfg").dump(data)

    def setup_cfg_to_environment_yml(self):
        dgaf.files.ENVIRONMENT.dump({})

    def setup_cfg_to_requirements_txt(self):
        data = dgaf.files.SETUPCFG.load()
        if hasattr(data, "to_dict"):
            data = data.to_dict()
        dgaf.files.REQUIREMENTS.write_text(data["options"]["install_requires"])

    def to_setup_cfg(self):

        data = dgaf.io.File("setup.cfg").load()

        for x in "metadata options".split():
            if x not in data:
                data.add_section(x)

        metadata, options = data["metadata"], data["options"]
        if "name" not in metadata:
            metadata["name"] = "test"
        if "version" not in metadata:
            metadata["version"] = (
                __import__("datetime").date.today().strftime("%Y.%m.%d")
            )
        if "description" not in metadata:
            metadata["description"] = ""
        if "long_description" not in metadata:
            metadata["long_description"] = f"file: {dgaf.files.README}"

        if "include_package_data" not in options:
            options["include_package_data"] = True
        if "packages" not in options:
            options["packages"] = "find:"

        dgaf.base.File("setup.cfg").dump(data)

    def __iter__(self):
        # explicitly configure how do it works.
        yield task("doit.cfg", ..., dgaf.files.DOITCFG, [])

        # seed the setup.cfg declarative configuration file.
        if self.develop or self.install:
            yield task(
                "setup.cfg", self.CONTENT, dgaf.files.SETUPCFG, self.to_setup_cfg
            )

        # get the current state of the setup.
        state = dgaf.base.File(dgaf.files.SETUPCFG).load()

        if self.discover:
            # discover the packages for the project.
            if hasattr(state, "to_dict"):
                state = state.to_dict()

            # discover dependencies in the content with depfinder and append the results.
            yield task(
                "discover-dependencies",
                self.CONTENT + [state, dgaf.files.SETUPCFG],
                ...,
                self.discover_dependencies,
            )

        if self.conda:
            yield install_task("ensureconda", actions=["ensureconda"])
            yield task(
                "discover-conda-environment",
                [state, dgaf.files.SETUPCFG],
                dgaf.files.ENVIRONMENT,
                self.setup_cfg_to_environment_yml,
            )
        elif self.develop or self.install:
            # we'll install these when we make the project.
            pass
        else:
            yield task(
                "discover-pip-requirements",
                [state, dgaf.files.SETUPCFG],
                dgaf.files.REQUIREMENTS,
                self.setup_cfg_to_requirements_txt,
            )

        if self.lint:
            yield install_task("pre_commit")
            yield task(
                "infer-pre-commit",
                self.CONTENT,
                dgaf.files.PRECOMMITCONFIG,
                [],
            )
            yield task(
                "install-pre-commit-hooks",
                [dgaf.files.PRECOMMITCONFIG, dgaf.files.PRECOMMITCONFIG.load()],
                ...,
                "pre-commit install-hooks",
            )
        if self.test:
            if self.ci:
                extras = []

            if not self.smoke and dgaf.files.TOX:
                yield install_task("tox")
            else:
                yield install_task("pytest")

        if self.docs:
            yield install_task("jupyter_book")


@dataclasses.dataclass
class Develop(Start):
    def __iter__(self):
        yield from super().__iter__()

        if self.conda:
            # update teh conda environemnt
            yield task(
                "update-conda",
                dgaf.files.ENVIRONMENT,
                ...,
                f"conda env update -f {dgaf.files.ENVIRONMENT}",
            )
        elif not (self.install or self.develop):
            # update the pip environment
            yield task(
                "update-pip",
                dgaf.files.REQUIREMENTS,
                ...,
                f"pip install -r {dgaf.files.REQUIREMENTS}",
            )

        if self.install:
            # install to site packages.
            yield task("install-package", self.CONTENT, ..., "pip install .")
        elif self.develop:
            # make a setup.py to use in develop mode
            yield task("setup.py", dgaf.files.SETUPCFG, dgaf.files.SETUPPY, [])
            yield task(
                "develop-package",
                self.CONTENT + [dgaf.files.SETUPPY],
                ...,
                "pip install -e .",
            )

        if self.lint:
            yield task(
                "format-lint", self.FILES, ..., "python -m pre_commit --all-files"
            )

        if self.test:
            if not self.smoke and dgaf.files.TOX:
                # can we infer a good tox test
                yield task("test-tox", self.CONTENT + [TOX], ..., "tox")
            else:
                yield task(
                    "test-pytest", self.CONTENT + [dgaf.files.PYPROJECT], ..., "pytest"
                )

        if self.docs:
            # make toc
            # make config
            yield task(
                "build-html-docs",
                self.CONTENT + [dgaf.files.TOC, dgaf.files.CONFIG],
                ["build/html"],
                "jb build .",
            )
