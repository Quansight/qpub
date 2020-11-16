"""converters.py"""
import dgaf
from dgaf import File, merge
from dgaf.files import *


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
