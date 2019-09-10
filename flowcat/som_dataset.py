from __future__ import annotations
from dataclasses import dataclass, field
from dataslots import with_slots
from typing import List, Tuple, Dict

import numpy as np
import pandas as pd

from tensorflow import keras

from flowcat import utils, io_functions
from flowcat.dataset.som import SOM


def pad_array(array, pad_width):
    if pad_width > 0:
        array = np.pad(array, pad_width=[
            (pad_width, pad_width),
            (pad_width, pad_width),
            (0, 0),
        ], mode="wrap")
    return array


@with_slots
@dataclass
class SOMCase:
    """Wrapper for SOM data, associating it with additional classification
    metadata."""

    label: str
    group: str = None
    soms: Dict[str, utils.URLPath] = field(default_factory=dict)
    data: Dict[str, np.array] = field(default_factory=dict)

    def get_tube(self, tube: str, store: bool = False) -> SOM:
        if tube not in self.data:
            sompath = self.soms[tube]
            data = np.load(sompath)
            if store:
                self.data[tube] = np.load(sompath)
            return data
        return self.data[tube]

    def __repr__(self):
        return f"<SOMCase {self.label} {self.group}"


def load_som_cases(row, path, tubes):
    sompath = path / row["label"]
    soms = {
        tube: sompath + f"_t{tube}.npy" for tube in tubes
    }
    return SOMCase(soms=soms, group=row["group"], label=row["label"])


@with_slots
@dataclass
class SOMDataset:
    """Simple wrapper for reading dataset metadata."""

    data: pd.Series  # [SOMCase]
    config: dict  # Dict of dims and channels from tubes

    @classmethod
    def from_path(cls, path):
        config = io_functions.load_json(path + "_config.json")
        metadata = io_functions.load_csv(path + ".csv")
        tubes = list(config.keys())
        som_cases = metadata.apply(load_som_cases, axis=1, args=(path, tubes))
        return cls(data=som_cases, config=config)

    @property
    def labels(self):
        return np.array([s.group for s in self.data])

    @property
    def group_counts(self):
        return {
            group: len(data)
            for group, data in self.data.groupby(by=lambda s: self.data[s].group)
        }

    def filter_groups(self, groups: List[str]) -> SOMDataset:
        newgroup = self.data[self.data.apply(lambda c: c.group in groups)]
        return self.__class__(newgroup, config=self.config)

    def get_tube(self, tube: int) -> List[SOM]:
        return [s.get_tube(tube) for s in self.data]

    def split(self, ratio: float, stratified: bool = True) -> Tuple[SOMDataset, SOMDataset]:
        if stratified:
            trains = []
            valids = []
            for group, data in self.data.groupby(by=lambda s: self.data[s].group):
                data.reset_index(drop=True, inplace=True)
                data = data.reindex(np.random.permutation(data.index))
                pivot = round(ratio * len(data))
                trains.append(data[:pivot])
                valids.append(data[pivot:])
            train = pd.concat(trains)
            validate = pd.concat(valids)
        else:
            data = self.data.reindex(np.random.permutation(data.index))
            pivot = round(ratio * len(data))
            train = data[pivot:]
            validate = data[:pivot]

        # reset index and shuffle randomly
        train.reset_index(drop=True, inplace=True)
        train = train.reindex(np.random.permutation(train.index))
        validate.reset_index(drop=True, inplace=True)
        validate = validate.reindex(np.random.permutation(validate.index))

        return (
            self.__class__(train, config=self.config),
            self.__class__(validate, config=self.config),
        )

    def balance(self, num_per_group: int) -> SOMDataset:
        """Randomly upsample groups with samples less than num_per_group,
        randomly downsample groups with samples more than num_per_group."""
        groups = []
        all_data = self.data

        for _, gdata in all_data.groupby(by=lambda s: all_data[s].group):
            groups.append(gdata.sample(num_per_group, replace=True))

        new_data = pd.concat(groups)
        self.data = new_data
        self.data.reset_index(drop=True, inplace=True)
        self.data = self.data.reindex(np.random.permutation(self.data.index))
        return self

    def balance_per_group(self, num_per_group: dict) -> SOMDataset:
        """Randomly upsample groups in dict to the given count."""
        groups = []
        all_data = self.data

        for name, gdata in all_data.groupby(by=lambda s: all_data[s].group):
            try:
                num = num_per_group[name]
                groups.append(gdata.sample(num, replace=True))
            except KeyError:
                continue

        new_data = pd.concat(groups)
        self.data = new_data
        self.data.reset_index(drop=True, inplace=True)
        self.data = self.data.reindex(np.random.permutation(self.data.index))
        return self

    def map_groups(self, mapping: dict) -> SOMDataset:
        """Map cases to new groups given inside the dict."""
        for case in self.data:
            case.group = mapping.get(case.group, case.group)
        return self

    def __len__(self):
        return self.data.shape[0]

    def __repr__(self):
        return f"<SOMDataset {len(self)} cases>"


class SOMSequence(keras.utils.Sequence):

    def __init__(
            self,
            dataset: SOMDataset,
            binarizer,
            tube: List[str],
            batch_size: int = 32,
            pad_width: int = 0):
        self.dataset = dataset
        self.tube = tube
        self.batch_size = batch_size
        self.binarizer = binarizer
        self.pad_width = pad_width

        self._cache = {}

    @property
    def true_labels(self):
        return self.dataset.groups

    def __len__(self) -> int:
        return int(np.ceil(len(self.dataset) / float(self.batch_size)))

    def __getitem__(self, idx: int) -> Tuple[np.array, np.array]:
        if idx in self._cache:
            return self._cache[idx]

        batch = self.dataset[idx * self.batch_size:(idx + 1) * self.batch_size]

        inputs = []
        for tube in self.tube:
            x_batch = np.array([
                pad_array(
                    s.get_tube(tube, kind="som").get_data().data,
                    self.pad_width,
                ) for s in batch
            ])
            inputs.append(x_batch)

        y_labels = [s.group for s in batch]
        y_batch = self.binarizer.transform(y_labels)
        self._cache[idx] = inputs, y_batch
        return inputs, y_batch
