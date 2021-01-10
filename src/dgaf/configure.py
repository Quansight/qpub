"""configure packages, documentation, and tests."""

from .__init__ import *
import shutil
import doit
import pathlib
import asyncio
import sys
import json
import textwrap


def task_requirements():
    def requirements():
        chapter = Chapter()
        REQUIREMENTS_TXT.update(pip_requirements(chapter.include))

    return Task(actions=[requirements], targets=[REQUIREMENTS_TXT])


def task_environment():
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


def task_python():
    return Task(file_dep=[REQUIREMENTS_TXT], targets=[PYPROJECT_TOML])


def task_setup():
    return Task(file_dep=[REQUIREMENTS_TXT], targets=[SETUP_CFG, SETUP_PY])


def task_jb():
    return Task(targets=[TOC, CONFIG])


def task_conf():
    return Task(targets=[CONF])


def ignore(cache={}):
    """initialize the path specifications to decide what to omit."""
    import importlib.resources

    if cache:
        return cache

    def where_template(template):
        try:
            with importlib.resources.path("dgaf.templates", template) as template:
                template = pathlib.Path(template)
        except:
            template = pathlib.Path(__file__).parent / "templates" / template
        return template

    for file in (
        "Python.gitignore",
        "Nikola.gitignore",
        "JupyterNotebooks.gitignore",
    ):
        import pathspec

        file = where_template(file)
        for pattern in (
            file.read_text().splitlines()
            + ".local .vscode _build .gitignore .git .doit.db* .benchmarks".split()
        ):
            if bool(pattern):
                match = pathspec.patterns.GitWildMatchPattern(pattern)
                if match.include:
                    cache[pattern] = match
    return cache


def ignored_by(object):
    for k, v in ignore().items():
        try:
            next(v.match([str(object)]))
            return k
        except StopIteration:
            continue


def ignored(object):
    return bool(ignored_by(object))


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
        import yaml, requests_cache

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


if __name__ == "__main__":

    main(globals())