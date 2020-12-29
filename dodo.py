# ██████╗  ██████╗ ██╗████████╗    ████████╗ █████╗ ███████╗██╗  ██╗███████╗
# ██╔══██╗██╔═══██╗██║╚══██╔══╝    ╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝██╔════╝
# ██║  ██║██║   ██║██║   ██║          ██║   ███████║███████╗█████╔╝ ███████╗
# ██║  ██║██║   ██║██║   ██║          ██║   ██╔══██║╚════██║██╔═██╗ ╚════██║
# ██████╔╝╚██████╔╝██║   ██║          ██║   ██║  ██║███████║██║  ██╗███████║
# ╚═════╝  ╚═════╝ ╚═╝   ╚═╝          ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝


def task_python_gitignore():
    """download the gitignore file for excluding python content."""
    import pathlib

    dgaf = pathlib.Path("dgaf")
    targets = [
        dgaf / "templates" / "Python.gitignore",
        dgaf / "templates" / "Nikola.gitignore",
        dgaf / "templates" / "JupyterNotebooks.gitignore",
    ]

    return dict(
        actions=[
            """wget https://raw.githubusercontent.com/github/gitignore/master/Python.gitignore -O dgaf/templates/Python.gitignore""",
            """wget https://raw.githubusercontent.com/github/gitignore/master/community/Python/Nikola.gitignore -O dgaf/templates/Nikola.gitignore""",
            """wget https://raw.githubusercontent.com/github/gitignore/master/community/Python/ .gitignore -O dgaf/templates/JupyterNotebooks.gitignore""",
        ],
        targets=targets,
        uptodate=list(map(pathlib.Path.exists, targets)),
    )
