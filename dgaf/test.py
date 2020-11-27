import dgaf


class Test(dgaf.base.Project):
    """test the package"""

    def __iter__(self):
        if dgaf.files.TOX in self.FILES:
            yield from Tox.__iter__(self)
        else:
            yield from Pytest.__iter__(self)


class Pytest(Test):
    def __iter__(self):
        # add dependencies based on the environment
        yield dict(
            name="install test dependencies",
            actions=["pip install pytest"],
            uptodate=[dgaf.util.is_installed("pytest")],
        )
        yield dict(
            name="test the package",
            file_dep=[],  # content
            actions=["pytest"],
            targets=[],  # should target a test report
        )


class Tox(Test):
    def __iter__(self):
        # add dependencies based on the environment
        yield dict(
            name="install test dependencies",
            actions=["pip install tox"],
            uptodate=[dgaf.util.is_installed("tox")],
        )
        yield dict(
            name="test the package",
            file_dep=[],  # content
            actions=["tox"],
            targets=[],  # should target a test report
        )
