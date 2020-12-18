def task_python_gitignore():
    """download the gitignore file for excluding python content."""
    import pathlib

    return dict(
        actions=[
            """wget https://raw.githubusercontent.com/github/gitignore/master/Python.gitignore -O dgaf/Python.gitignore"""
        ],
        targets=["dgaf/Python.gitignore"],
        uptodate=[pathlib.Path("dgaf/Python.gitignore").exists()],
    )
