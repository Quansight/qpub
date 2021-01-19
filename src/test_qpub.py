# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.9.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # `qpub` tests
#

# %% [markdown]
# one way to use qpub is it with the `doit` line magic; load the `qpub` ipython extension with

# %%
import pathlib, pytest, os, sys
def build(pytester, object, where=None):
    for key, value in object.items():
        if isinstance(value, str):
            file = (where or pathlib.Path()) / key
            if where:
                where.mkdir(exist_ok=True, parents=True)
            if file.suffix == ".ipynb":
                import nbformat
                value = nbformat.v4.writes(nbformat.v4.new_notebook(cells=[
                    nbformat.v4.new_code_cell(contents)]))
            pytester.makefile(file.suffix, **{
                str(file.with_suffix("")): value
            })
        elif isinstance(value, dict):
            build(pytester, value, where=(where or pathlib.Path())/key)


# %% [markdown]
# for this test document we'll consider a simple project with the contents below. in the `contents`, we need to explicitly provide a docstring and version to cooperate with `flit`s model.

# %%
meta = """'''my projects docstring'''
__version__ = "0.0.1"
"""
contents = """
import pandas
"""

# %% [markdown]
# it allows different layouts, like `python_layouts` to be used as test input.

# %%
flit_layouts = [{
    "my_idea.py": meta+contents
}, dict(
    my_idea={
        "__init__.py": meta+contents
    }
), dict(
    src=dict(
        my_idea={
            "__init__.py": meta+contents
        }
    )
), {
    "my_idea.ipynb": meta+contents
}]

# %%
setuptools_layouts = [{
    "1969-12-9-my-idea.ipynb": meta+contents
}, {
    "test_my_idea.ipynb": meta+contents
}, {"my_idea.py": contents}]


# %%
def run(pytester, cmd):
    result = pytester.run(*cmd.split())
    assert not result.ret, "\n".join((result.outlines+result.errlines))
    return result


# %%
def verify_pyproject():
    """verify metadata for pyproject"""
    import qpub

    data = qpub.PYPROJECT_TOML.load()

    # qpub can infer configurations for different tools.
#     assert data["tool"]["poetry"]
    assert data["tool"]["flit"]
    assert data["tool"]["pytest"]

    assert (
        data["tool"]["flit"]["metadata"]["module"]
#         == data["tool"]["poetry"]["name"]  
        == "my_idea")

#     assert data["tool"]["poetry"]["version"] == "0.0.1"
#     assert data["tool"]["poetry"]["description"]

    assert "pandas" in data["tool"]["flit"]["metadata"]["requires"]

    assert "pytest" in data["tool"]["flit"]["metadata"]["requires-extra"]["test"]

#     assert "pandas" in data["tool"]["poetry"]["dependencies"]
#     assert "pytest" in data["tool"]["poetry"]["dev-dependencies"]


# %%
def verify_setuptools():
    """verify metadata for pyproject"""
    import qpub 
    data = qpub.SETUP_CFG.load()
    print(11, data._sections)
    assert data["metadata"]["name"] == "my_idea"



# %%
@pytest.mark.parametrize("layout", setuptools_layouts)
def test_non_flit_projects(pytester, layout):
    import qpub
    build(pytester, layout)
    print(qpub.get_name())
    assert qpub.get_name()=="my_idea"

    # at this point we just have content and no configuration
    assert not (pytester.path / qpub.PYPROJECT_TOML).exists()

    # infer the flit configuration by default if the module complies with the doc version conventions.
    run(pytester, "qpub pyproject.toml")
    # no a pyproject configuration exists that contains flit metadata
    assert (pytester.path / qpub.PYPROJECT_TOML).exists()

    
    # forget the task explicitly, can't forget the file, to update with poetry
    # generally we wouldn't have to forget tasks, but we do for testing
    run(pytester, "qpub forget pyproject requirements_txt")

    # update the poetry metadata
    # mock the dependency resolution to speed up the tests alot!
#     run(pytester, "qpub pyproject -b poetry")

    verify_pyproject()


    assert not (pytester.path / qpub.SETUP_CFG).exists()

    # configure the setuptools configuration.
    run(pytester, "qpub forget pyproject")
    run(pytester, "qpub pyproject -b setuptools")
    assert (pytester.path / qpub.SETUP_CFG).exists()

    verify_setuptools()
    # need to test overriding build backends

    # configure documentation files
    run(pytester, "qpub toc config mkdocs_yml")
    assert (pytester.path / qpub.TOC).exists()
    assert (pytester.path / qpub.CONFIG).exists()

    # configure linter files
    run(pytester, "qpub precommit")


# %%
@pytest.mark.parametrize("layout", flit_layouts)
def test_flit_projects(pytester, layout):
    import qpub
    build(pytester, layout)
    print(qpub.get_name())
    assert qpub.get_name()=="my_idea"

    # at this point we just have content and no configuration
    assert not (pytester.path / qpub.PYPROJECT_TOML).exists()

    # infer the flit configuration by default if the module complies with the doc version conventions.
    run(pytester, "qpub pyproject.toml")
    # no a pyproject configuration exists that contains flit metadata
    assert (pytester.path / qpub.PYPROJECT_TOML).exists()

    assert qpub.is_flit()
    
    # forget the task explicitly, can't forget the file, to update with poetry
    # generally we wouldn't have to forget tasks, but we do for testing
    run(pytester, "qpub forget pyproject requirements_txt")

    # update the poetry metadata
    # mock the dependency resolution to speed up the tests alot!
#     run(pytester, "qpub pyproject -b poetry")

    verify_pyproject()


    assert not (pytester.path / qpub.SETUP_CFG).exists()

    # configure the setuptools configuration.
    run(pytester, "qpub forget pyproject")
    run(pytester, "qpub pyproject -b setuptools")
    assert (pytester.path / qpub.SETUP_CFG).exists()

    verify_setuptools()
    # need to test overriding build backends

    # configure documentation files
    run(pytester, "qpub toc config mkdocs_yml")
    assert (pytester.path / qpub.TOC).exists()
    assert (pytester.path / qpub.CONFIG).exists()

    # configure linter files
    run(pytester, "qpub precommit")
