import nbconvert
import git


class Nikola(nbconvert.exporters.NotebookExporter):
    """add nikola metadata to a notebook based on the union of the resources and git."""

    def from_notebook_node(self, nb, resources=None, **kw):
        print(resources)
        return nb, resources
