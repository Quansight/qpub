import dgaf
from dgaf.files import *
from dgaf.util import task, action
from subprocess import run
import doit

dgaf.converters.content_to_deps = dgaf.converters.to_deps

# anything using action right now will not raise. it needs to be replaced with something that will.

DOIT_CONFIG = {"backend": "sqlite3", "verbosity": 2, "par_type": "thread"}


@task(CONTENT)
def _make_requirements() -> REQUIREMENTS:
    """infer requirements.txt files from partial package information.

    the requirements are inferred from content and other configuration files.

    requirements exist in: CONTENT, REQUIREMENTS, PYPROJECT, SETUPCFG"""
    dependencies = dgaf.util.depfinder(*CONTENT)

    REQUIREMENTS.dump(list(dependencies.union(REQUIREMENTS.load())))


@task([REQUIREMENTS] + INITS)
def _make_pyproject():
    """use poetry to make the pyproject

    is everything poetry related weird"""
    data = PYPROJECT.load()

    if not data["/build-system"]:
        run(
            "python -m poetry config virtualenvs.create false".split()
        )  # pollute the environment
        if not data["/tool/poetry"]:
            # a native doit wrapped because this method escapes the doit process.
            run("python -m poetry init --no-interaction".split())


@task(_make_pyproject, [PYPROJECT, POETRYLOCK], uptodate=REQUIREMENTS.read_text())
def _add_dependencies():
    """add dependencies with poetry"""
    data = PYPROJECT.load()
    data["/tool/poetry/scripts"] = data["/entrypoints/console_scripts"]
    PYPROJECT.dump(data)

    run("python -m poetry add ".split() + list(REQUIREMENTS.load()), check=True)


@task(POETRYLOCK, SETUPPY)
def _make_python_setup():
    """make a setuppy to work in develop mode"""

    dgaf.converters.poetry_to_setup()
    run("python -m black setup.py".split())


@task(CONTENT, INITS)
def _initialize_python():
    """make all of the directies importable."""
    dgaf.converters.to_python_modules()


@task(REQUIREMENTS)
def _install_pip():
    """install packages from pypi."""
    run(f"python -m pip install -r {REQUIREMENTS}".split(), check=True)
    # maybe use poetry in install mode?


setup_tasks = [_install_pip]


@task(PYPROJECT, uptodate=" ".join(sorted(PYPROJECT.load()["/tool"])))
def _install_develop_dependencies():
    """peek into PYPROJECT and install the dev tools"""
    extras = dgaf.converters.to_dev_requirements()
    if extras:
        run("poetry add -D".split() + list(extras), check=True)


@task([_install_develop_dependencies, SETUPPY])
def develop():
    """install a package in development mode"""
    # no way like the old way
    run("python -m pip install setuptools".split())
    run("python setup.py develop".split(), check=True)


@task(CONTENT + [PYPROJECT])
def install():
    """install a package.
    this should use setup.cfg in the future."""
    run("python -m pip install .".split(), check=True)


@task([_install_develop_dependencies] + CONTENT)
def test():
    """test a project"""
    # allow for tox and basic unittests at some point.
    # can we foorce hypothesis testing
    run("python -m pytest".split(), check=True)


@task([_install_develop_dependencies] + CONTENT)
def lint():
    tool = PYPROJECT.load()["/tool"]
    if "flakehell" in tool:
        run("python -m flakehell lint".split(), check=True)
    elif "flake8" in tool:
        ...


@task(PYPROJECT)
def build():
    """use either new or old python convetions to build a wheel."""
    data = PYPROJECT.load()
    if data["/build-system/build-backend"].startswith("flit_core"):
        run("python -m flit build".split(), check=True)
    elif data["/build-system/build-backend"].startswith("poetry"):
        run("python -m poetry build".split(), check=True)
    else:
        """make setuppy and build with setuptools"""


@task(SETUPPY)
def _build_py():
    """build a python wheel with setup.py"""
    run("python setup.py sdist bdist_wheel".split(), check=True)


if CONDA:

    @task(REQUIREMENTS, ENVIRONMENT)
    def _make_environment():
        """extend the environment.yml conda from discovered imports."""
        dgaf.converters.pip_to_conda()

    @task(ENVIRONMENT)
    def _conda_update():
        """update a conda if conda is available."""
        run(f"conda update -f {ENVIRONMENT}".split(), check=True)

    setup_tasks = [_conda_update] + setup_tasks


@task(setup_tasks)
def setup():
    """setup environmetns with conda and pip.`"""


if __name__ == "__main__":
    __import__("doit").run(globals())
