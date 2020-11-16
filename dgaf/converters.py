"""converters.py"""
import dgaf
from dgaf import File, merge
from dgaf.files import *


def to_deps():
    pyproject = PYPROJECT.load()
    dependencies = (
        set(dgaf.util.depfinder(*FILES))
        .union(pyproject["/tool/flit/metadata/requires"] or [])
        .union(list(pyproject["/tool/poetry/dependencies"] or []))
        .union(REQUIREMENTS.load())
    )
    # .union(ENVIRONMENT.load())
    # .union(SETUP.load())

    for x in "python".split():
        x in dependencies and dependencies.remove(x)

    return list(dependencies)


def pip_to_conda(write=True, to=None):
    to = to or ENVIRONMENT
    data = dict(dependencies=list(REQUIREMENTS.load()))
    cmd = doit.tools.CmdAction(
        " ".join(["conda install --dry-run --json"] + REQUIREMENTS.load())
    )
    cmd.execute()
    result = dgaf.util.Dict(__import__("json").loads(cmd.out))

    if "error" in result:
        if result["/packages"]:
            env = to.load()
            env["dependencies"] = [
                x for x in env["dependencies"] if x not in result["packages"]
            ]
            for dep in env["dependencies"]:
                if isinstance(dep, dict) and "pip" in dep:
                    pip = dep
            else:
                pip = dict(pip=[])
                env["dependencies"].append(pip)

            pip["pip"] = list(set(pip["pip"]).union(result["packages"]))

            if "pip" not in env["dependencies"]:
                env["dependencies"] += ["pip"]

            env["dependencies"] = list(
                set(x for x in env["dependencies"] if isinstance(x, str))
            ) + [pip]

            ENVIRONMENT.dump(env)
    if write:
        to.dump(to.load(), **data)
    return data


def to_flit(write=True, to=PYPROJECT):
    current = merge(to.load(), dgaf.template.poetry)
    metadata = {
        "author": current["/tool/flit/metadata/author"] or REPO.commit().author.name,
        "author-email": current["/tool/flit/metadata/author-email"]
        or REPO.commit().author.email,
        "keywords": current["/tool/flit/metadata/keywords"] or "",
        "home-page": current["/tool/flit/metadata/home-page"]
        or REPO.remote("origin").url.rstrip(".git"),
        "description-file": current["/tool/flit/metadata/description-file"]
        or str(README),
        "requires": list(
            set(
                (current["/tool/flit/metadata/requires"] or [])
                + [x for x in REQUIREMENTS.load() if not x.startswith("git+")]
            )
        ),
    }

    if TOP_LEVEL:
        if len(TOP_LEVEL) == 1:
            metadata["module"] = current["/tool/flit/metadata/module"] or str(
                TOP_LEVEL[0]
            )
    data = merge(current, dict(tool=dict(flit=dict(metadata=metadata))))

    data["/tool/flit/metadata/requires"] = [
        x for x in data["/tool/flit/metadata/requires"] if not x.startswith("git+")
    ]
    if write:
        to.dump(data)
    return data


def flit_to_setup():
    """convert flit metadata to an executable setuptools fiile."""
    metadata = PYPROJECT.load()["/tool/flit/metadata"]
    ep = PYPROJECT.load()["/tool/flit/entrypoints"]
    if ep:
        for k, v in ep.items():
            ep[k] = list(map(" = ".join, v.items()))
    setup = dict(
        name=metadata["module"],
        version=__import__("datetime").date.today().strftime("%Y.%m.%d"),
        author=metadata["author"],
        author_email=metadata["author-email"],
        description="",
        long_description=README.read_text(),
        long_description_content_type="text/markdown",
        url=metadata["home-page"],
        # license="BSD-3-Clause",
        install_requires=metadata["requires"],
        # include_package_data=True,
        packages=[metadata["module"]],
        classifiers=[],
        cmdclass={},
        entry_points=ep,
    )

    SETUP.write_text(
        f"""__name__ == "__main__" and __import__("setuptools").setup(**{
        __import__("json").dumps(setup)
    })"""
    )


def to_conda():
    import json
    import doit

    pip = REQUIREMENTS.load()
    cmd = doit.tools.CmdAction(" ".join(["conda install --dry-run --json"] + pip))

    cmd.execute()
    result = json.loads(cmd.out)
    env = merge(
        ENVIRONMENT.load(),
        dict(name="notebook", channels=["conda-forge"], dependencies=pip),
    )
    if "success" in result:
        ENVIRONMENT.dump(env)
        return
    if "error" in result:
        if result.get("packages"):
            env["dependencies"] = [
                x for x in env["dependencies"] if x not in result["packages"]
            ]
            for dep in env["dependencies"]:
                if isinstance(dep, dict) and "pip" in dep:
                    pip = dep
            else:
                pip = dict(pip=[])
                env["dependencies"].append(pip)
            pip["pip"] = list(set(pip["pip"]).union(result["packages"]))

            if pip["pip"] and "pip" not in env["dependencies"]:
                env["dependencies"] += ["pip"]

            env["dependencies"] = list(
                set(x for x in env["dependencies"] if isinstance(x, str))
            ) + [pip]

            ENVIRONMENT.dump(env)