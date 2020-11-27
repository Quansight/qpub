import dgaf


class Docs(dgaf.base.Project):

    """jupyter book is the most permissive collection of tools are polyglot documentation using `sphinx`"""

    def to_toc(self):

        """create `"_toc.yml"` that defines the layout of the articles. there are probably a few different ways to infer this.
        i don't think this is an easy problem.
        `"readme.md"` takes precedence in the sections."""

    def to_config(self):

        """infer the configuration information for the documentation and create or update `"_config.yml"`"""

    def __iter__(self):
        yield dict(
            name="table of contents",
            actions=[self.to_toc],
            targets=[dgaf.files.TOC],
        )
        yield dict(
            name="configure book",
            actions=[self.to_config],
            targets=[dgaf.files.CONFIG],
        )
        yield dict(
            name="install jupyter book",
            actions=["pip install jupyter-book"],
            uptodate=[dgaf.util.is_installed("jupyter_book")],
        )


class HTML(Docs):
    def __iter__(self):
        yield from super().__iter__()
        yield dict(
            name="build the content",
            file_dep=["_config.yml", "_toc.yml"],
            actions=[f"jb build . --toc {dgaf.files.TOC} --config {dgaf.files.CONFIG}"],
            targets=["_build/html"],
        )


class Blog(dgaf.base.Project):

    """jupyter book is the most permissive collection of tools are polyglot documentation using `sphinx`"""

    def to_conf_py(self):

        """create a `"conf.py"` for `nikola` to build a blog's content."""

    def __iter__(self):
        yield dict(
            name="configuration nikola blog",
            actions=[self.to_conf_py],
            targets=["conf.py"],
        )
        yield dict(
            name="build the blog",
            actions=["nikola build"],
        )
