""""doit tasks for dgaf.


tasks are used when actions add or updates files.
"""
from .__init__ import *
import sys

doit = __import__("doit")


class Reporter(doit.reporter.ConsoleReporter):
    def execute_task(self, task):
        self.outstream.write("MyReporter --> %s\n" % task.title())


DOIT_CONFIG = dict(verbosity=2, reporter=Reporter)


def task_docs():
    """configure the documentation"""
    docs = project / DOCS
    doit = __import__("doit")
    backend = project.docs_backend()
    # basically we wanna combine a bunch of shit
    if backend == "mkdocs":
        return dict(
            file_dep=project.all_files(),
            actions=[(doit.tools.create_folder, [docs]), project.to(Mkdocs).add],
            targets=[project / MKDOCS],
        )
    # nbdev, lektor can go here.
    return dict(
        file_dep=project.all_files(),
        actions=[(doit.tools.create_folder, [docs]), project.to(JupyterBook).add],
        targets=[project / CONFIG, project / TOC],
    )


def task_lint():
    """configure formatters and linters"""
    return dict(
        file_dep=project.all_files(),
        actions=[project.to(Lint).add],
        targets=[project / PRECOMMITCONFIG_YML],
    )


def task_python():
    """configure the python project"""
    targets = [project / PYPROJECT_TOML]
    backend = project.python_backend()

    if backend == "setuptools":
        targets += [project / SETUP_CFG]
        actions = [project.to(Setuptools).add]
    elif backend == "flit":
        actions = [project.to(Flit).add]
    elif backend == "poetry":
        requires = " ".join(project.get_requires())
        actions = [project.to(Poetry).add, f"poetry add --lock {requires}"]
    return dict(file_dep=project.all_files(), actions=actions, targets=targets)


def task_build():
    backend = project.python_backend()
    return dict(
        file_dep=[project / PYPROJECT_TOML],
        actions=["python -m pep517.build ."],
        targets=[project.to_whl(), project.to_sdist()],
    )


def task_setup_py():
    actions = []
    if not SETUP_PY.exists():
        actions += [
            lambda: SETUP_PY.write_text("""__import__("setuptools").setup()\n""")
            and None
        ]
    return dict(file_dep=[SETUP_CFG], actions=actions, targets=[SETUP_PY])


def task_requirements():
    """configure the requirements.txt for the project"""
    return dict(actions=[project.to(Pip).add], targets=[project / REQUIREMENTS_TXT])


def task_conda():
    """configure a conda environment for the distribution"""

    def shuffle_conda():
        doit = __import__("doit")
        file = project / ENVIRONMENT_YAML
        env = file.load()
        c, p = [], []
        for dep in env.get("dependencies", []):
            if isinstance(dep, str):
                c += [dep]
            elif isinstance(dep, dict):
                p = dep.pop("pip", [])
        if c:
            action = doit.tools.CmdAction(
                f"""conda install --dry-run -cconda-forge {" ".join(c)}"""
            )
            if action.err:
                print(action, util.packages_from_conda_not_found(action.err.strip()))
                for package in util.packages_from_conda_not_found(action.err.strip()):
                    p.append(c.pop(c.index(package)))
                if p:
                    if "pip" not in c:
                        c += ["pip", dict(pip=p)]

                file.write(dict(dependencies=c))

    return dict(
        actions=[project.to(Conda).add, shuffle_conda],
        targets=[project / ENVIRONMENT_YAML],
    )


def task_gitignore():
    """create a gitignore for the distribution"""
    project = Gitignore()
    return dict(file_dep=project.all_files(), actions=[], targets=[project / GITIGNORE])


def task_ci():
    """configure a ci workflow for test and release a project"""
    project = Actions()
    return dict(actions=[project.add], targets=[project / BUILDTESTRELEASE])


def task_readthedocs():
    """configure for the distribution for readthedocs"""
    project = Readthedocs()
    return dict(actions=[project.add], targets=[project / READTHEDOCS])


def task_build():
    "building wheel and source distribution"
    return dict(
        file_dep=[PYPROJECT_TOML],
        actions=["python -m pep517.build ."],
        targets=[],
        # targets=[project.to_whl(), project.to_sdist()]
    )


def task_jupyter_book():
    """build the documentation with jupyter book"""
    docs = project / "docs"
    return dict(
        file_dep=[project / TOC, project / CONFIG] + project.all_files(),
        actions=[
            "jb build --path-output docs --toc docs/_toc.yml --config docs/_config.yml ."
        ],
        targets=[BUILD / "html"],
        uptodate=[],
    )


def task_uml():
    """generate a uml diagram of the project with pyreverse."""
    return dict(
        file_dep=project.all_files(),
        actions=[f"pyreverse pyreverse -o png -k {project.get_name()}"],
        targets=[project.path / "classes.png", project.path / "packages.png"],
    )


def task_mkdocs():
    """build the documentation with mkdocs"""
    return dict(file_dep=[MKDOCS], actions=["mkdocs build"], targets=[BUILD / "mkdocs"])


def task_blog():
    """build a blog site with nikola"""
    return dict(file_dep=[CONF], actions=["nikola build"], targets=[BUILD / "nikola"])


def task_pdf():
    """build a pdf version of the documentation"""
    return dict(actions=[])


def main(argv=None):
    global project
    if argv is None:
        argv = __import__("sys").argv[1:]
    project = Project()
    main = doit.doit_cmd.DoitMain(doit.cmd_base.ModuleTaskLoader(globals()))

    sys.exit(main.run(argv))


if __name__ == "__main__":
    main()