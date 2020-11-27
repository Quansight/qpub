import dgaf, doit, textwrap


class Package(dgaf.base.Project):

    """a package can be built builts, installed, or developed with."""

    def directories_to_modules(self):
        """make all directories accessible by python imports by populating missing `"__init__.py"` files."""

        for init in self.INITS:
            if not init:
                init.touch()

    def to_setup_cfg(self):
        """infer a [declarative packaging configuration](https://setuptools.readthedocs.io/en/latest/userguide/declarative_config.html) for the project.
        the `"setup.cfg"` can be used to install, develop, or build using `setuptools`.
        with the modern `"pyproject.toml"` conventions the `setuptools.build_meta` system can used to build from this file."""
        data = dgaf.base.File("setup.cfg").load()

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
        if "install_requires" not in options:
            options["install_requires"] = """"""
        options["install_requires"] = (
            ""  # str(options["install_requires"])
            + "\n"
            + textwrap.indent("\n".join(dgaf.converters.to_deps()), " " * 4)
        )

        dgaf.base.File("setup.cfg").dump(data)

    def __iter__(self):
        yield dict(
            name="add __init__ conventions",
            file_dep=self.CONTENT,
            actions=[self.directories_to_modules],
            targets=self.INITS,
        )
        state = dgaf.files.SETUPCFG.load()
        if hasattr(state, "to_dict"):
            state = state.to_dict()
        yield dict(
            name=str(dgaf.files.SETUPCFG),
            file_dep=self.CONTENT,
            actions=[self.to_setup_cfg],
            targets=[dgaf.files.SETUPCFG],
            uptodate=[doit.tools.config_changed(state)],
        )


class Develop(Package):
    def to_setup_py(self):
        """create a setup.py needed to run things in development mode.
        https://setuptools.readthedocs.io/en/latest/setuptools.html#setup-cfg-only-projects"""

        dgaf.files.SETUPPY.write_text("""__import__("setuptools").setup()""".strip())

    def __iter__(self):
        yield from super().__iter__()
        yield dict(
            name=str(dgaf.files.SETUPPY),
            file_dep=[dgaf.files.SETUPCFG],
            actions=[
                self.to_setup_py,
            ],
            targets=[dgaf.files.SETUPPY],  # targets link to site-packages
        )
        state = dgaf.files.SETUPCFG.load()
        if hasattr(state, "to_dict"):
            state = state.to_dict()
        yield dict(
            name="install in editable mode",
            file_dep=[dgaf.files.SETUPCFG],
            actions=["python -m pip install -e."],
            uptodate=[doit.tools.config_changed(state)],
        )


class Install(Package):
    def setup_cfg_to_pyproject(self):

        """it is an emerging for convention for packaging projects using the `"pyproject.toml"` convention;
        this concept is discussed in PEP 517 & 518.

        we really just need to add the build system after making the setup.cfg."""

        data = dgaf.files.PYPROJECT.load()
        data.update(
            {
                "build-system": {
                    "requires": ["setuptools", "wheel"],
                    "build-backend": "setuptools.build_meta",
                },
            }
        )
        dgaf.files.PYPROJECT.dump(data)

    def __iter__(self):
        yield dict(
            name="pyproject",
            file_dep=[dgaf.files.SETUPCFG],
            actions=[self.setup_cfg_to_pyproject],
            targets=[dgaf.files.PYPROJECT],
            uptodate=[doit.tools.config_changed(dgaf.files.SETUPCFG.load())],
        )
        yield dict(
            name="install",
            file_dep=self.CONTENT + [dgaf.files.PYPROJECT],
            actions=["pip install ."],
        )


class Build(Package):

    """`Build` the project as a `wheel`.
    https://pypi.org/project/pep517/


    [pep517]: https://setuptools.readthedocs.io/en/latest/userguide/quickstart.html#basic-use"""

    def __iter__(self):
        yield dict(
            name="build dependencies",
            actions=["python -m pip install pep517"],
            uptodate=[dgaf.util.is_installed("pep517")],
        )
        yield dict(
            name="build the package",
            file_dep=[dgaf.files.PYPROJECT],
            actions=["python -m pep517.build ."],
            targets=["dist"],
        )


class Uninstall(Package):

    """`Build` the project as a `wheel`.
    https://pypi.org/project/pep517/


    [pep517]: https://setuptools.readthedocs.io/en/latest/userguide/quickstart.html#basic-use"""

    def __iter__(self):
        yield dict(
            name="build dependencies",
            actions=["python -m pip uninstall test"],
        )