import nbconvert


class Nikola(nbconvert.exporters.NotebookExporter):
    """add nikola metadata to a notebook based on the union of the resources and git."""

    def from_notebook_node(self, nb, resources=None, **kw):
        # should use git information to accumulate the resources.
        nb.metadata.update(nikola=dict(resources["metadata"]))
        nb, resources = super().from_notebook_node(nb, resources, **kw)
        resources["output_suffix"] = ""  # this causes an inplace overwrite
        return nb, resources
