from .__init__ import *

DOIT_CONFIG = dict(verbosity=2)


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
    doit = __import__("doit")

    if options.python == "infer":
        options.python = "flit"

    if SETUP_PY in project.files:
        options.python = "setuptools"

    uptodate = [doit.tools.config_changed(options.python)]
    if options.python == "flit":
        return dict(
            file_dep=[x for x in project.files if x in {".py", ".ipynb"}],
            actions=[project.to_flit],
            task_dep=[],
            targets=[project.path / PYPROJECT_TOML],
            uptodate=uptodate,
        )
    if options.python == "poetry":
        requires = " ".join(project.get_requires())
        test_requires = " ".join(project.get_test_requires())

        return dict(
            file_dep=[x for x in project.files if x in {".py", ".ipynb"}],
            actions=[
                project.to_poetry,
                f"""poetry add {requires} --lock""",
                f"""poetry add {test_requires} --dev --lock""",
            ],
            task_dep=[],
            targets=[project.path / PYPROJECT_TOML],
            uptodate=uptodate,
            verbosity=2,
        )

    if options.python == "setuptools":
        return dict(task_dep=["setup_py"], uptodate=uptodate)

    raise UnknownBackend(
        f"""{options.python} is not one of {
        "infer flit poetry setuptools"
    }"""
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
    docs = project / "docs"

    return dict(
        actions=[
            (doit.tools.create_folder, [docs]),
            project.to_toc_yml,
            project.to_config_yml,
        ],
        targets=[docs / TOC, docs / CONFIG],
        uptodate=[doit.tools.config_changed(" ".join(map(str, project.files)))],
    )


if __name__ == "__main__":
    import sys

    doit = __import__("doit")
    project = Project()
    main = doit.doit_cmd.DoitMain(doit.cmd_base.ModuleTaskLoader(globals()))
    main.run(["list"])
    sys.exit(main.run(sys.argv[1:]))
