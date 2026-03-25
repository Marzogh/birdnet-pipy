"""Location-based species filtering for bird detection models.

Provides a LocationFilter abstraction that decouples location filtering
from the audio detection model. Implementations include:

- NoFilter: passthrough (no filtering)
- ModelBackedFilter: adapter wrapping a model's filter_by_location() (V2.4)
- GeoModelFilter: standalone ONNX geomodel inference (V3.0+)
"""

import datetime
import logging
import threading
from abc import ABC, abstractmethod
from collections import OrderedDict

import numpy as np

from config.constants import DEFAULT_SPECIES_FILTER_THRESHOLD

from .label_utils import get_scientific_name, parse_geomodel_labels

logger = logging.getLogger(__name__)


def _date_to_geomodel_week(dt: datetime.datetime) -> int:
    """Convert a datetime to geomodel week number (1-48, 4 weeks per month).

    Matches the week encoding used by the geomodel training pipeline
    (gbifutils.py:date_to_week).
    """
    week = (dt.month - 1) * 4
    if dt.day <= 7:
        week += 1
    elif dt.day <= 14:
        week += 2
    elif dt.day <= 21:
        week += 3
    else:
        week += 4
    return week


class LocationFilter(ABC):
    """Abstract base class for location-based species filtering."""

    @abstractmethod
    def load(self) -> None:
        """Load all resources into memory. Called by the factory."""

    @abstractmethod
    def filter(
        self,
        lat: float,
        lon: float,
        dt: datetime.datetime,
        threshold: float = DEFAULT_SPECIES_FILTER_THRESHOLD,
    ) -> list[str] | None:
        """Return species labels likely at a location and time.

        Args:
            lat: Latitude in degrees (-90 to 90).
            lon: Longitude in degrees (-180 to 180).
            dt: Recording timestamp (each implementation extracts the week
                format it needs).
            threshold: Minimum probability to include a species.

        Returns:
            List of BirdNET species labels (e.g. "SciName_CommonName")
            that should be allowed, or None if filtering is not available.
        """


class NoFilter(LocationFilter):
    """Passthrough filter — no location-based filtering."""

    def load(self) -> None:
        pass

    def filter(self, lat, lon, dt, threshold=DEFAULT_SPECIES_FILTER_THRESHOLD):
        return None


class ModelBackedFilter(LocationFilter):
    """Adapter that delegates to a model's filter_by_location() method.

    Used for V2.4 which has an embedded meta model.
    """

    def __init__(self, model):
        self._model = model

    def load(self) -> None:
        # Model is already loaded by the time this is created.
        pass

    def filter(self, lat, lon, dt, threshold=DEFAULT_SPECIES_FILTER_THRESHOLD):
        week = dt.isocalendar()[1]
        return self._model.filter_by_location(lat, lon, week, threshold)


class GeoModelFilter(LocationFilter):
    """Location filter using a standalone ONNX geomodel.

    Loads an ONNX model that predicts species occurrence probabilities
    from (lat, lon, week) and cross-references output indices with
    BirdNET model labels.
    """

    def __init__(
        self,
        model_path: str,
        labels_path: str,
        birdnet_labels: list[str],
    ):
        self._model_path = model_path
        self._labels_path = labels_path
        self._birdnet_labels = birdnet_labels

        # Populated by load()
        self._session = None
        self._input_name: str | None = None
        self._output_name: str | None = None

        # Index mapping: geomodel output index → BirdNET label string
        self._index_to_birdnet_label: dict[int, str] = {}
        # BirdNET labels with no geomodel equivalent (always allowed through)
        self._unmapped_labels: list[str] = []

        self._cache: OrderedDict[tuple, list[str]] = OrderedDict()
        self._cache_max_size = 128
        self._inference_lock = threading.Lock()

    def load(self) -> None:
        """Load ONNX session, parse labels, build cross-reference mapping."""
        import onnxruntime as ort

        self._session = ort.InferenceSession(
            self._model_path, providers=['CPUExecutionProvider']
        )
        self._input_name = self._session.get_inputs()[0].name
        self._output_name = self._session.get_outputs()[0].name

        geomodel_labels = parse_geomodel_labels(self._labels_path)
        self._build_label_mapping(geomodel_labels)

        logger.info(
            "Geomodel loaded",
            extra={
                'model': self._model_path,
                'geomodel_species': len(geomodel_labels),
                'mapped_species': len(self._index_to_birdnet_label),
                'unmapped_birdnet_species': len(self._unmapped_labels),
            },
        )

    def _build_label_mapping(self, geomodel_labels: list[tuple[str, str, str]]) -> None:
        """Build cross-reference between geomodel indices and BirdNET labels.

        Uses scientific name as the join key.
        """
        # BirdNET labels are "SciName_CommonName" — extract sci name for lookup
        birdnet_by_sci: dict[str, str] = {}
        for label in self._birdnet_labels:
            birdnet_by_sci[get_scientific_name(label)] = label

        # Map geomodel index → BirdNET label (via scientific name)
        mapped_sci_names: set[str] = set()
        for idx, (_code, sci_name, _com_name) in enumerate(geomodel_labels):
            birdnet_label = birdnet_by_sci.get(sci_name)
            if birdnet_label is not None:
                self._index_to_birdnet_label[idx] = birdnet_label
                mapped_sci_names.add(sci_name)

        # BirdNET labels whose sci names have no geomodel equivalent
        self._unmapped_labels = [
            label for sci, label in birdnet_by_sci.items()
            if sci not in mapped_sci_names
        ]

    def filter(self, lat, lon, dt, threshold=DEFAULT_SPECIES_FILTER_THRESHOLD):
        if self._session is None:
            raise RuntimeError("GeoModelFilter not loaded. Call load() first.")

        geomodel_week = _date_to_geomodel_week(dt)
        cache_key = (lat, lon, geomodel_week, threshold)

        with self._inference_lock:
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
                logger.debug("Geomodel cache hit", extra={
                    'lat': lat, 'lon': lon, 'week': geomodel_week,
                    'cached_species_count': len(self._cache[cache_key]),
                })
                return self._cache[cache_key]

            # Run ONNX inference
            model_input = np.array([[lat, lon, geomodel_week]], dtype=np.float32)
            output = self._session.run(
                [self._output_name], {self._input_name: model_input}
            )
            probs = output[0][0]  # shape: (n_species,)

            # Filter by threshold, map to BirdNET labels
            local_species = []
            for idx, birdnet_label in self._index_to_birdnet_label.items():
                if idx < len(probs) and probs[idx] >= threshold:
                    local_species.append(birdnet_label)

            # Always include unmapped BirdNET species (no data to exclude them)
            local_species.extend(self._unmapped_labels)

            self._cache[cache_key] = local_species
            if len(self._cache) > self._cache_max_size:
                self._cache.popitem(last=False)

        logger.debug("Geomodel inference", extra={
            'lat': lat, 'lon': lon, 'week': geomodel_week,
            'above_threshold': len(local_species) - len(self._unmapped_labels),
            'unmapped': len(self._unmapped_labels),
            'total_allowed': len(local_species),
        })

        return local_species
