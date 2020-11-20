import dgaf
from dgaf.files import *

from dgaf.util import task, action

dgaf.converters.content_to_deps = dgaf.converters.to_deps

DOIT_CONFIG = {"backend": "sqlite3", "verbosity": 2, "par_type": "thread"}


@task(CONTENT, REQUIREMENTS)
def make_requirements(task):
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
    import doit

    action(
        "poetry config virtualenvs.create false"
    ).execute()  # pollute the environment
    if not data["/tool/poetry"]:
        # a native doit wrapped because this method escapes the doit process.
        doit.tools.LongRunning("poetry init --no-interaction").execute()


@task(PYPROJECT, POETRYLOCK)
def add_dependencies():
    """add dependencies with poetry"""

    data = PYPROJECT.load()
    data["/tool/poetry/scripts"] = data["/entrypoints/console_scripts"]
    PYPROJECT.dump(data)

    action("poetry add ", REQUIREMENTS.load()).execute()


@task(POETRYLOCK, SETUPPY)
def make_python_setup():
    """make a setuppy to work in develop mode"""
    dgaf.converters.poetry_to_setup()
    action("black setup.py").execute()


@task(SETUPPY)
def develop():
    """install a package in development mode"""
    # no way like the old way
    action("pip install setuptools").execute()
    action("python setup.py develop").execute()


@task(REQUIREMENTS)
def install_pip():
    """install packages from pypi."""
    action(f"pip install -r {REQUIREMENTS}").execute()
    # maybe use poetry in install mode?


setup_tasks = [install_pip]


@task(CONTENT + [PYPROJECT])
def install():
    """install a package.

    this should use setup.cfg in the future."""
    action("pip install .").execute()


@task(CONTENT)
def test():
    """test a project"""
    # allow for tox and basic unittests at some point.
    # can we foorce hypothesis testing
    action("pytest").execute()


@task(PYPROJECT)
def build():
    """use either new or old python convetions to build a wheel."""
    data = PYPROJECT.load()
    if data["/build-system/build-backend"].startswith("flit_core"):
        action("flit build").execute()
    elif data["/build-system/build-backend"].startswith("poetry"):
        action("poetry build").execute()
    else:
        """make setuppy and build with setuptools"""


@task(SETUPPY)
def build_py():
    """build a python wheel with setup.py"""
    action("python setup.py sdist bdist_wheel").execute()


if CONDA:

    @task(REQUIREMENTS, ENVIRONMENT)
    def make_environment():
        """extend the environment.yml conda from discovered imports."""
        dgaf.converters.pip_to_conda()

    @task(ENVIRONMENT)
    def conda_update():
        """update a conda if conda is available."""
        action(f"conda update -f {ENVIRONMENT}").execute()

    setup_tasks = [conda_update] + setup_tasks


@task(setup_tasks)
def setup():
    """setup environmetns with conda and pip.`"""


if __name__ == "__main__":
    __import__("doit").run(globals())