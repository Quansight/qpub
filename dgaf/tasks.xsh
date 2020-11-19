import dgaf
from dgaf.files import *

from dgaf.util import task
$RAISE_SUBPROC_ERROR = True

dgaf.converters.content_to_deps = dgaf.converters.to_deps

@task(CONTENT, REQUIREMENTS)
def make_requirements(task):
    """generate requirements.txt files from partial package information.
    
    the requirements are inferred from content and other configuration files.
    
    requirements exist in: CONTENT, REQUIREMENTS, PYPROJECT, SETUPCFG"""
    dependencies = dgaf.util.depfinder(*CONTENT)
    REQUIREMENTS.dump(list(dependencies.union(REQUIREMENTS.load())))

@task(REQUIREMENTS, PYPROJECT)
def make_pyproject(task):
    """use poetry to make the pyproject"""
    data = PYPROJECT.load()
    if 'poetry' not in data['/tool']:
        try:
            ![poetry init --no-interaction]
        except:pass
    
    ![poetry add @(REQUIREMENTS.load())]

@task(PYPROJECT, SETUPPY)
def make_python_setup(task):
    """make a setuppy to work in develop mode"""
    dgaf.converters.flit_to_setup()

@task(SETUPPY)
def develop(task):
    """install a package in development mode"""
    ![pip install -e .]

@task(REQUIREMENTS)
def install_pip(task):
    """install packages from pypi."""
    ![pip install -r @(REQUIREMENTS)]
    # maybe use poetry in install mode?

setup_tasks = [install_pip]

@task(SETUPPY)
def install_develop(task):
    """install a package in development mode.
    
    this should use setup.cfg in the future."""
    ![pip install -e.]

@task(PYPROJECT)
def install(task):
    """install a package.
    
    this should use setup.cfg in the future."""
    ![pip install .]

@task(CONTENT)
def test(task):
    """test a project"""
    # allow for tox and basic unittests at some point.
    # can we foorce hypothesis testing
    pytest

@task(PYPROJECT)
def build(task):
    """use either new or old python convetions to build a wheel."""
    data = PYPROJECT.load()
    if data['/build-system/build-backend'].startswith("flit_core"):
        flit build
    elif data['/build-system/build-backend'].startswith("poetry"):
        poetry build
    else:
        """make setuppy and build with setuptools"""
        

@task(SETUPPY)
def build_py(task):
    """build a python wheel with setup.py"""
    python setup.py sdist bdist_wheel


if CONDA:
    @task(REQUIREMENTS, ENVIRONMENT)
    def make_environment(task):
        """extend the environment.yml conda from discovered imports."""
        dgaf.converters.pip_to_conda()


    @task(ENVIRONMENT)
    def conda_update(task):
        """update a conda if conda is available."""
        conda env update @(ENVIRONMENT)

    setup_tasks = [conda_update] +setup_tasks


@task(setup_tasks)
def setup(task):
    """setup environmetns with conda and pip.`"""

if __name__ == '__main__':
    __import__("doit").run(globals())