"""configure packages, documentation, and tests."""

import asyncio
import json
import pathlib
import shutil
import sys
import textwrap

import doit

from . import (
    BUILD,
    CONF,
    CONFIG,
    CONVENTIONS,
    DOCS,
    DOIT_CONFIG,
    ENVIRONMENT_YAML,
    PYPROJECT_TOML,
    REQUIREMENTS_TXT,
    SETUP_CFG,
    SETUP_PY,
    TOC,
    Chapter,
    Param,
    Path,
    Repo,
    Task,
    get_license,
    get_name,
    get_python_version,
    get_repo,
    is_private,
    main,
    merge,
    options,
    templated_file,
)


def task_requirements_txt():
    """infer the project dependencies and write them to a requirements.txt"""

    def requirements():
        chapter = Chapter()
        REQUIREMENTS_TXT.update(pip_requirements(chapter.source_files()))

    return Task(actions=[requirements], targets=[REQUIREMENTS_TXT], clean=True)


def task_environment_yaml():
    """infer the project dependencies and write them to an environment.yaml"""

    def conda():
        conda = pypi_to_conda(REQUIREMENTS_TXT.load())
        pip = []
        # try to solve for these.
        ENVIRONMENT_YAML.update(
            dict(dependencies=conda + (pip and ["pip", dict(pip=pip)] or []))
        )

    return Task(
        actions=[conda], file_dep=[REQUIREMENTS_TXT], targets=[ENVIRONMENT_YAML]
    )


def task_pyproject():
    """infer the pyproject.toml configuration for the project"""

    def python(backend):
        repo = Repo(get_repo())

        if backend == "flit":
            data = templated_file(
                "flit.json",
                dict(
                    name=get_name(),
                    requires=REQUIREMENTS_TXT.load(),
                    author=repo.get_author(),
                    email=repo.get_email(),
                    license=get_license(),
                    classifiers=[],
                    keywords=[],
                    python_version=">=" + get_python_version(),
                    test_requires=[],
                    docs_requires=[],
                    url=repo.get_url(),
                ),
            )

            PYPROJECT_TOML.update(data)

        if backend == "poetry":
            pass

        if backend == "setuptools":
            pass

    return Task(
        file_dep=[REQUIREMENTS_TXT],
        actions=[python],
        targets=[PYPROJECT_TOML],
        params=[
            Param(
                "backend",
                "flit",
                choices=tuple((x, x) for x in ("flit", "poetry", "setuptools")),
            )
        ],
    )


def task_setup_cfg():
    """infer the declarative setup.cfg configuration for the project"""
    return Task(file_dep=[REQUIREMENTS_TXT], targets=[SETUP_CFG, SETUP_PY])


def task_toc():
    """infer the table of contents for the jupyter_book documentation."""

    def main():
        TOC.write(get_section(Chapter()))

    return Task(actions=[main], targets=[TOC])


def task_config():
    """infer the jupyter_book documentation configuration."""

    def main():
        repo = Repo(get_repo())
        chapter = Chapter()
        data = templated_file(
            "_config.json",
            dict(
                name=get_name(),
                requires=REQUIREMENTS_TXT.load(),
                author=repo.get_author(),
                exclude=[str(x / "*") for x in chapter.exclude_directories]
                + [str(BUILD)],
            ),
        )
        CONFIG.update(data)

    return Task(actions=[main], targets=[CONFIG])


def task_mkdocs_yml():
    """infer the mkdocs documentation configuration."""

    return Task()


def task_blog():
    """infer the nikola blog documentation configuration."""

    return Task(targets=[CONF])


def get_section(chapter, parent=Path(), *done, **section):
    """generate the nested jupyter book table of contents format for the chapter."""
    files = [
        x
        for x in chapter.include
        if 1 == (len(x.parts) - len(parent.parts))
        and x.is_relative_to(parent)
        and x not in CONVENTIONS
        and not is_private(x)
    ]
    index = None
    for name in "index readme".split():
        for file in files:
            if file.stem.lower() == name:
                index = file
                if "file" not in section:
                    section.update(file=str(file.with_suffix("")), sections=[])
                else:
                    section["sections"].append(str(file.with_suffix("")))

    if index is None:
        section = dict(file=None, sections=[])

    for file in files:
        if file == index:
            continue
        if file.suffix in {".py", ".ipynb", ".md", ".rst"}:
            index = file
            if section["file"] is None:
                section["file"] = str(file.with_suffix(""))
            else:
                section["sections"].append(dict(file=str(file.with_suffix(""))))

    for dir in [DOCS] + [
        x
        for x in chapter.directories
        if x.is_relative_to(parent) and x not in CONVENTIONS and not is_private(x)
    ]:
        if dir == parent:
            continue
        if dir not in done:
            section["sections"].append(get_section(chapter, dir, *done))
            if section["sections"][-1]["file"] == None:
                section["sections"].pop(-1)
            done += (dir,)

    return section


def rough_source(nb):
    """extract a rough version of the source in notebook to infer files from"""

    if isinstance(nb, str):
        nb = json.loads(nb)

    return "\n".join(
        textwrap.dedent("".join(x["source"]))
        for x in nb.get("cells", [])
        if x["cell_type"] == "code"
    )


def _import_depfinder():
    if "depfinder" not in sys.modules:
        import requests_cache
        import yaml

        dir = Path(__file__).parent
        requests_cache.install_cache(str(options.cache / "requests_cache"))
        dir.mkdir(parents=True, exist_ok=True)
        if not hasattr(yaml, "CSafeLoader"):
            yaml.CSafeLoader = yaml.SafeLoader
        import depfinder

        requests_cache.uninstall_cache()
    return __import__("depfinder")


async def infer(file):
    """infer imports from different kinds of files."""
    import aiofiles

    depfinder = _import_depfinder()

    async with aiofiles.open(file, "r") as f:
        if file.suffix not in {".py", ".ipynb", ".md", ".rst"}:
            return file, {}
        source = await f.read()
        if file.suffix == ".ipynb":
            source = rough_source(source)
        try:
            return (file, depfinder.main.get_imported_libs(source).describe())
        except SyntaxError:
            return file, {}


async def infer_files(files):
    return dict(await asyncio.gather(*(infer(file) for file in map(Path, set(files)))))


def gather_imports(files):
    """"""

    object = infer_files(files)
    try:
        return dict(asyncio.run(object))
    except RuntimeError:
        __import__("nest_asyncio").apply()
        return dict(asyncio.run(object))


def merged_imports(files):
    results = merge(*gather_imports(files).values())
    return sorted(
        set(list(results.get("required", [])) + list(results.get("questionable", [])))
    )


def import_to_pypi(list):
    global IMPORT_TO_PIP
    if not IMPORT_TO_PIP:
        depfinder = _import_depfinder()
        IMPORT_TO_PIP = {
            x["import_name"]: x["pypi_name"] for x in depfinder.utils.mapping_list
        }
    return [IMPORT_TO_PIP.get(x, x) for x in list if x not in ["src"]]


def pypi_to_conda(list):
    global PIP_TO_CONDA

    if not PIP_TO_CONDA:
        depfinder = _import_depfinder()
        PIP_TO_CONDA = {
            x["import_name"]: x["conda_name"] for x in depfinder.utils.mapping_list
        }
    return [PIP_TO_CONDA.get(x, x) for x in list]


def pip_requirements(files):
    return import_to_pypi(merged_imports(files))


IMPORT_TO_PIP = None
PIP_TO_CONDA = None

if not REQUIREMENTS_TXT.exists():
    DOIT_CONFIG["default_tasks"] += ["requirements"]

if shutil.which("mamba") or shutil.which("conda") and not ENVIRONMENT_YAML.exists():
    DOIT_CONFIG["default_tasks"] += ["environment"]


DOIT_CONFIG["default_tasks"] += ["toc"]
DOIT_CONFIG["default_tasks"] += ["config"]

if __name__ == "__main__":
    main(globals())
