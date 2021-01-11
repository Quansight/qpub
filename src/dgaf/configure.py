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


def get_section(chapter, parent=Path(), *done, **section):
    files = [
        x
        for x in chapter.include
        if 1 == (len(x.parts) - len(parent.parts))
        and x.is_relative_to(parent)
        and x not in CONVENTIONS
        and not is_private(x)
    ]
    for name in "index readme".split():
        for file in files:
            if file.stem.lower() == name:
                if "file" not in section:
                    section.update(file=file.stem, sections=[])
                else:
                    sections["sections"].append(file.stem)

    if "file" not in section:
        section = dict(file=None, sections=[])

    for file in files:
        if file.suffix in {".py", ".ipynb", ".md", ".rst"}:
            if section["file"] is None:
                section["file"] = file.stem
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
            done += (dir,)

    return section


def task_jb():
    def main():
        TOC.write(get_section(Chapter()))

    return Task(actions=[main], targets=[TOC, CONFIG])


def task_conf():
    return Task(targets=[CONF])


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