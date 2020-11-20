import dgaf
from dgaf.files import *
from dgaf.util import task, action
from subprocess import run
import doit

dgaf.converters.content_to_deps = dgaf.converters.to_deps

# anything using action right now will not raise. it needs to be replaced with something that will.

DOIT_CONFIG = {"backend": "sqlite3", "verbosity": 2, "par_type": "thread"}


@task(CONTENT, REQUIREMENTS)
def make_requirements():
    """generate requirements.txt files from partial package information.

    the requirements are inferred from content and other configuration files.

    requirements exist in: CONTENT, REQUIREMENTS, PYPROJECT, SETUPCFG"""
    dependencies = dgaf.util.depfinder(*CONTENT)
    REQUIREMENTS.dump(list(dependencies.union(REQUIREMENTS.load())))


@task([REQUIREMENTS] + INITS, PYPROJECT)
def make_pyproject():
    """use poetry to make the pyproject

    is everything poetry related weird"""
    data = PYPROJECT.load()

    if not data["/build-system"]:
        run(
            "python -m poetry config virtualenvs.create false".split()
        )  # pollute the environment
        if not data["/tool/poetry"]:
            # a native doit wrapped because this method escapes the doit process.
            run(
                "python -m poetry init --no-interaction".split(),
            )


@task(PYPROJECT, POETRYLOCK)
def add_dependencies():
    """add dependencies with poetry"""

    data = PYPROJECT.load()
    data["/tool/poetry/scripts"] = data["/entrypoints/console_scripts"]
    PYPROJECT.dump(data)

    run("python -m poetry add ".split() + list(REQUIREMENTS.load()), check=True)


@task(POETRYLOCK, SETUPPY)
def make_python_setup():
    """make a setuppy to work in develop mode"""
    dgaf.converters.poetry_to_setup()
    run("python -m black setup.py".split())


@task(CONTENT, INITS)
def initialize_python():
    """make all of the directies importable."""
    dgaf.converters.to_python_modules()


@task(REQUIREMENTS)
def install_pip():
    """install packages from pypi."""
    run(f"python -m pip install -r {REQUIREMENTS}".split(), check=True)
    # maybe use poetry in install mode?


setup_tasks = [install_pip]


@task([PYPROJECT, POETRYLOCK])
def install_develop():
    """peek into PYPROJECT and install the dev tools"""
    extras = dgaf.converters.to_dev_requirements()
    if extras:
        run("poetry add -D".split() + list(extras), check=True)


@task([install_develop, SETUPPY])
def develop():
    """install a package in development mode"""
    # no way like the old way
    run("python -m pip install setuptools".split())
    run("python setup.py develop".split(), check=True)


@task(CONTENT + [POETRYLOCK])
def install():
    """install a package.
    this should use setup.cfg in the future."""
    run("python -m pip install .".split(), check=True)


@task(CONTENT)
def test():
    """test a project"""
    # allow for tox and basic unittests at some point.
    # can we foorce hypothesis testing
    run("python -m pytest".split(), check=True)


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
def build_py():
    """build a python wheel with setup.py"""
    run("python setup.py sdist bdist_wheel".split(), check=True)


if CONDA:

    @task(REQUIREMENTS, ENVIRONMENT)
    def make_environment():
        """extend the environment.yml conda from discovered imports."""
        dgaf.converters.pip_to_conda()

    @task(ENVIRONMENT)
    def conda_update():
        """update a conda if conda is available."""
        run(f"conda update -f {ENVIRONMENT}".split(), check=True)

    setup_tasks = [conda_update] + setup_tasks


@task(setup_tasks)
def setup():
    """setup environmetns with conda and pip.`"""


if __name__ == "__main__":
    __import__("doit").run(globals())
