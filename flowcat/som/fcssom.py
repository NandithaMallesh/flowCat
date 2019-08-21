from __future__ import annotations
from typing import Union, Iterable, Generator
import logging

import numpy as np
import pandas as pd

import tensorflow as tf

from flowcat.dataset.fcs import FCSData, join_fcs_data
from flowcat.dataset.case import TubeSample
from flowcat.utils import load_json, save_json, URLPath, save_joblib, load_joblib
from flowcat.preprocessing import scalers
from .base import SOM
from .tfsom import create_initializer, TFSom


MARKER_IMAGES = {
    "cd45_ss": ("CD45-KrOr", "SS INT LIN", None),
    "ss_cd19": (None, "SS INT LIN", "CD19-APCA750"),
    "kappa_lambda": (None, "Kappa-FITC", "Lambda-PE"),
    "zz_cd45_ss_cd19": ("CD45-KrOr", "SS INT LIN", "CD19-APCA750"),
}

MARKER_IMAGES_NAME_ONLY = {
    "cd45_ss": ("CD45", "SS INT LIN", None),
    "ss_cd19": (None, "SS INT LIN", "CD19"),
    "kappa_lambda": (None, "kappa", "lambda"),
    "zz_cd45_ss_cd19": ("CD45", "SS INT LIN", "CD19"),
}

LOGGER = logging.getLogger(__name__)


class MarkerMissingError(Exception):
    def __init__(self, markers, message):
        self.markers = markers
        self.message = message


class InvalidScaler(Exception):
    pass


def create_color_map(weights, cols, name="colormap", img_size=None):
    """Create a color map using given cols. Also generate a small reference visualizing the given colorspace.
    Params:
        weights: Tensor of weights with nodes in rows and marker channels in columns.
        cols: number of columns used for the image. needs to be of length 3
        name: Name of the generated image
        img_size: Size of generated image, otherwise will be inferred as sqrt of weight row count.
    """
    assert len(cols) == 3, "Needs one column for each color, use None to ignore a channel."
    rows = weights.shape[0]
    if img_size is None:
        side_len = int(np.sqrt(rows))
        img_size = (side_len, side_len)

    slices = [
        tf.zeros(weights.shape[0]) if col is None else weights[:, col]
        for col in cols
    ]
    marker_image = tf.reshape(tf.stack(slices, axis=1), shape=(1, *img_size, 3))
    summary_image = tf.summary.image(name, marker_image)
    return summary_image


class FCSSom:
    """Transform FCS data to SOM node weights."""

    def __init__(
            self,
            dims,
            init=("random", None),
            markers=None,
            marker_name_only=False,
            marker_images=None,
            name="fcssom",
            scaler="MinMaxScaler",
            **kwargs):
        self.dims = dims
        m, n, dim = self.dims

        init_type, init_data = init
        if init_type == "random":
            init_data = init_data or 1
        elif init_type == "reference":
            assert isinstance(init_data, SOM)
            markers = init_data.markers
            rm, rn = init_data.dims
            init_data = init_data.data
            m = rm if m == -1 else m
            n = rn if n == -1 else n
        elif init_type == "sample":
            assert isinstance(init_data, FCSData)
            markers = init_data.markers
            init_data = init_data.data

        dim = len(markers) if dim == -1 else dim

        self.marker_name_only = marker_name_only
        self.name = name
        self.markers = list(markers)
        self._graph = tf.Graph()
        self.trained = False
        self.modelargs = {
            "init": init_type,
            "kwargs": kwargs,
        }

        with self._graph.as_default():
            initialization = create_initializer(init_type, init_data, (m, n, dim))

        self.model = TFSom(
            (m, n, dim),
            graph=self._graph,
            initialization=initialization,
            model_name=f"{self.name}",
            **kwargs)

        if marker_images and self.model.tensorboard:
            with self._graph.as_default():
                self.add_weight_images(marker_images)

        self.model.initialize()

        if scaler == "StandardScaler":
            self.scaler = scalers.FCSStandardScaler()
        elif scaler == "MinMaxScaler":
            self.scaler = scalers.FCSMinMaxScaler()
        else:
            if scaler is not None:
                self.scaler = scaler
            else:
                raise InvalidScaler(scaler)

    @classmethod
    def load(cls, path: Union[str, URLPath], **kwargs):
        path = URLPath(path)
        scaler = load_joblib(path / "scaler.joblib")
        config = load_json(path / "config.json")
        obj = cls(
            dims=config["dims"],
            scaler=scaler,
            name=config["name"],
            markers=config["markers"],
            marker_name_only=config["marker_name_only"],
            **{**config["modelargs"]["kwargs"], **kwargs},
        )
        obj.model.load(path / "model.ckpt")
        obj.trained = True
        return obj

    @property
    def config(self):
        return {
            "dims": self.dims,
            "name": self.name,
            "markers": self.markers,
            "trained": self.trained,
            "modelargs": self.modelargs,
            "marker_name_only": self.marker_name_only,
        }

    def add_weight_images(self, marker_dict):
        """
        Params:
            marker_dict: Dictionary of image name to 3-tuple of markers.
        """
        for name, markers in marker_dict.items():
            try:
                self.add_weight_image(name, markers)
            except MarkerMissingError as m:
                LOGGER.warning("Could not add %s missing %s", name, m.markers)

    def add_weight_image(self, name, markers):
        with tf.name_scope("WeightsSummary"):
            cols = []
            missing = []
            for marker in markers:
                if marker is None:
                    index = None
                else:
                    try:
                        index = self.markers.index(marker)
                    except ValueError:
                        missing.append(marker)
                        continue
                cols.append(index)
            if missing:
                raise MarkerMissingError(missing, "Failed to create weight image")

            color_map = create_color_map(
                self.model._weights, cols,
                name=name, img_size=(*self.dims[:2],))
            self.model.add_summary(color_map)

    @property
    def weights(self):
        data = self.model.output_weights
        dfdata = pd.DataFrame(data, columns=self.markers)
        return self._create_som(dfdata)

    def transform_args(self, scaler=None):
        if scaler is None:
            scaler = self.scaler
        return [
            (str(scaler.__class__), scaler.get_params())
        ]

    def _create_som(self, weights: np.array, scaler=None):
        data = pd.DataFrame(weights, columns=self.markers)
        return SOM(
            data,
            transforms=self.transform_args(scaler)
        )

    def save(self, path: URLPath):
        """Save the given model including scaler."""
        if not self.trained:
            raise RuntimeError("Model has not been trained")

        path.mkdir(parents=True, exist_ok=True)
        self.model.save(path / "model.ckpt")
        save_joblib(self.scaler, path / "scaler.joblib")
        save_json(self.config, path / "config.json")

    def train(self, data: Iterable[FCSData], sample: int = -1):
        """Input an iterable with FCSData
        Params:
            data: FCSData object
            sample: Optional subsample to be used in training
        """
        if self.marker_name_only:
            data = [d.marker_to_name_only() for d in data]

        joined = join_fcs_data(data, self.markers)

        if getattr(self.scaler, "fcsdata_scaler", False):
            joined = self.scaler.fit_transform(joined)
            res = joined.data
        else:
            res = joined.data
            res = self.scaler.fit_transform(res)

        if sample > 0:
            res = res[np.random.choice(res.shape[0], sample, replace=False), :]

        self.model.train(res)
        self.trained = True
        return self

    def transform(self, data: FCSData, sample: int = -1, label: str = "", scaler=None) -> SOM:
        """Transform input fcs into retrained SOM node weights."""
        data = data.align(self.markers, name_only=self.marker_name_only)

        scaler = scaler or self.scaler

        if getattr(scaler, "fcsdata_scaler", False):
            data = scaler.transform(data)
            res = data.data
        else:
            res = data.data
            res = scaler.transform(res)

        if sample > 0:
            res = res[np.random.choice(res.shape[0], sample, replace=False), :]

        weights = self.model.transform(res, label=label)
        somweights = self._create_som(weights, scaler=scaler)
        return somweights

    def transform_generator(
            self,
            data: Iterable[FCSData],
            sample: int = -1) -> Generator[SOM]:
        """Transform multiple samples."""
        for single in data:
            if isinstance(single, TubeSample):
                single = single.data
            yield self.transform(single, sample=sample)
