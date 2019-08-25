# pylint: skip-file
# flake8: noqa
from __future__ import annotations
from typing import List, Union
import re
import logging
from dataclasses import dataclass, field

from dataslots import with_slots
import numpy as np
import pandas as pd

from flowcat import utils, mappings


LOGGER = logging.getLogger(__name__)


@with_slots
@dataclass
class SOM:
    """Holds self organizing map data with associated metadata."""
    data: pd.DataFrame
    path: utils.URLPath = None
    cases: str = ""  # multiple should be separated by +
    tube: int = -1
    material: mappings.Material = None
    transforms: List[dict] = field(default_factory=list)

    @property
    def dims(self):
        rows = self.data.shape[0]
        sq_size = int(np.sqrt(rows))
        return (sq_size, sq_size)

    @property
    def markers(self):
        return self.data.columns.values

    @property
    def config(self):
        return {
            "cases": self.cases,
            "tube": self.tube,
            "transforms": self.transforms,
        }

    def np_array(self, pad_width=0):
        """Return as new numpy array. Optionally with padding by adding zeros
        to the borders of the SOM.

        Args:
            pad_width: Additional padding for SOM on borders. The width is
                       added to each border.
        """
        data = np.reshape(self.data.values, (*self.dims, -1))
        if pad_width:
            data = np.pad(data, pad_width=[
                (pad_width, pad_width),
                (pad_width, pad_width),
                (0, 0),
            ], mode="wrap")
        return data

    def __repr__(self):
        return f"<SOM {'x'.join(map(str, self.dims))} Tube:{self.tube}>"


@dataclass
class SOMCollection:
    """Holds multiple SOM, eg for different tubes for a single patient."""

    path: utils.URLPath = None
    cases: List[str] = field(default_factory=list)
    tubes: List[int] = field(default_factory=list)
    tubepaths: dict = field(default_factory=dict)

    def __post_init__(self):
        self._index = 0
        self._max_index = 0
        self._data = {}

    def load(self):
        """Load all tubes into cache."""
        for tube in self.tubes:
            self.get_tube(tube)

    def get_tube(self, tube):
        if tube in self._data:
            return self._data[tube]
        if tube not in self.tubes:
            return None
        path = self.tubepaths[tube]
        with path.open("r") as sfile:
            data = SOM(pd.read_csv(sfile, index_col=0), tube=tube, cases=self.cases)
        self._data[tube] = data
        return data

    def add_som(self, data):
        self._data[data.tube] = data
        if data.tube not in self.tubes:
            self.tubes.append(data.tube)

    @property
    def dims(self):
        if self.config:
            m = self.config("tfsom", "m")
            n = self.config("tfsom", "n")
        else:
            data = self.get_tube(self.tubes[0])
            return data.dims
        return (m, n)

    def __iter__(self):
        self._index = 0
        self._max_index = len(self.tubes)
        return self

    def __next__(self):
        if self._index < self._max_index:
            index = self._index
            self._index += 1
            return self.get_tube(self.tubes[index])
        raise StopIteration

    def __repr__(self):
        return f"<SOMCollection: Tubes: {self.tubes} Loaded: {len(self._data)}>"
