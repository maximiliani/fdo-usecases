"""Zenodo dataset design module."""

from fdo_usecases.designer_lib.executor import RecordDesign


class ZenodoDesign(RecordDesign):
    """Zenodo dataset record design."""

    def __init__(self, doi: str):
        """Initialize Zenodo design with DOI.

        Args:
            doi: Digital Object Identifier of the dataset

        """
        super().__init__()
        self.doi = doi
