import dgaf
from dgaf.files import *
from dgaf.util import task, action
import subprocess
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


@task(REQUIREMENTS, PYPROJECT)
def make_pyproject():
    """use poetry to make the pyproject

    is everything poetry related weird"""
    data = PYPROJECT.load()

    if not data["/build-system"]:
        subprocess.call(
            "python -m poetry config virtualenvs.create false".split()
        )  # pollute the environment
        if not data["/tool/poetry"]:
            # a native doit wrapped because this method escapes the doit process.
            subprocess.call(
                "python -m poetry init --no-interaction".split(),
            )


@task(PYPROJECT, POETRYLOCK)
def add_dependencies():
    """add dependencies with poetry"""

    data = PYPROJECT.load()
    data["/tool/poetry/scripts"] = data["/entrypoints/console_scripts"]
    PYPROJECT.dump(data)

    subprocess.call("python -m poetry add ".split() + list(REQUIREMENTS.load()))


@task(POETRYLOCK, SETUPPY)
def make_python_setup():
    """make a setuppy to work in develop mode"""
    dgaf.converters.poetry_to_setup()
    subprocess.call("python -m black setup.py".split())


@task(SETUPPY)
def develop():
    """install a package in development mode"""
    # no way like the old way
    subprocess.call("python -m pip install setuptools".split())
    subprocess.call("python setup.py develop".split())


@task(REQUIREMENTS)
def install_pip():
    """install packages from pypi."""
    subprocess.call(f"python -m pip install -r {REQUIREMENTS}".split())
    # maybe use poetry in install mode?


setup_tasks = [install_pip]


@task(CONTENT + [POETRYLOCK])
def install():
    """install a package.
    this should use setup.cfg in the future."""
    subprocess.call("python -m pip install .".split())


@task(CONTENT)
def test():
    """test a project"""
    # allow for tox and basic unittests at some point.
    # can we foorce hypothesis testing
    subprocess.call("python -m pytest".split())


@task(PYPROJECT)
def build():
    """use either new or old python convetions to build a wheel."""
    data = PYPROJECT.load()
    if data["/build-system/build-backend"].startswith("flit_core"):
        subprocess.call("python -m flit build".split())
    elif data["/build-system/build-backend"].startswith("poetry"):
        subprocess.call("python -m poetry build".split())
    else:
        """make setuppy and build with setuptools"""


@task(SETUPPY)
def build_py():
    """build a python wheel with setup.py"""
    subprocess.call("python setup.py sdist bdist_wheel".split())


if CONDA:

    @task(REQUIREMENTS, ENVIRONMENT)
    def make_environment():
        """extend the environment.yml conda from discovered imports."""
        dgaf.converters.pip_to_conda()

    @task(ENVIRONMENT)
    def conda_update():
        """update a conda if conda is available."""
        subprocess.call(f"conda update -f {ENVIRONMENT}".split())

    setup_tasks = [conda_update] + setup_tasks


@task(setup_tasks)
def setup():
    """setup environmetns with conda and pip.`"""


if __name__ == "__main__":
    __import__("doit").run(globals())
