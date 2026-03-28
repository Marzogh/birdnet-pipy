"""Abstract base class for bird detection models."""

import logging
from abc import ABC, abstractmethod

import numpy as np

from config.constants import DEFAULT_SPECIES_FILTER_THRESHOLD

from .label_utils import get_common_name
from .label_utils import get_ebird_code as _lookup_ebird_code

logger = logging.getLogger(__name__)


class BirdDetectionModel(ABC):
    """Abstract base class for bird detection models.

    All bird detection models must implement this interface to be usable
    by the inference server.
    """

    def __init__(self, ebird_codes_path: str | None = None):
        self.ebird_codes_path = ebird_codes_path

    @property
    @abstractmethod
    def name(self) -> str:
        """Model identifier (e.g., 'birdnet')."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Model version string (e.g., '2.4')."""

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """Required audio sample rate in Hz."""

    @property
    @abstractmethod
    def chunk_length_seconds(self) -> float:
        """Audio chunk length in seconds required for inference."""

    @abstractmethod
    def load(self) -> None:
        """Load all model resources into memory. Must be called before predict()."""

    @abstractmethod
    def predict(
        self,
        audio_chunk: np.ndarray,
        sensitivity: float = 1.0,
        cutoff: float = 0.0,
        chunk_index: int | None = None
    ) -> list[tuple[str, float]]:
        """Run inference on an audio chunk.

        Args:
            audio_chunk: Float32 array normalized to [-1, 1].
            sensitivity: Confidence adjustment parameter.
            cutoff: Minimum confidence threshold (0.0-1.0).
            chunk_index: Optional chunk index for logging.

        Returns:
            List of (species_label, confidence) tuples, sorted by confidence descending.
        """

    @abstractmethod
    def get_labels(self) -> list[str]:
        """Return all species labels this model can detect."""

    def get_ebird_code(self, scientific_name: str) -> str | None:
        """Look up eBird species code for a scientific name."""
        return _lookup_ebird_code(scientific_name)

    def _post_process(
        self,
        labels: list[str],
        scores: np.ndarray,
        cutoff: float,
        chunk_index: int | None = None
    ) -> list[tuple[str, float]]:
        """Log top results, apply cutoff threshold, filter and sort.

        Shared post-processing used by all model implementations after
        model-specific inference and score transformation.
        """
        # Verify labels and scores have matching lengths
        if len(labels) != len(scores):
            raise RuntimeError(
                f"Label count mismatch: {len(labels)} labels but {len(scores)} scores. "
                "Model and labels file may be out of sync."
            )

        # Log top 3 raw confidence scores before cutoff filtering
        if logger.isEnabledFor(logging.INFO):
            raw_scores = list(zip(labels, scores, strict=True))
            raw_scores_sorted = sorted(raw_scores, key=lambda x: x[1], reverse=True)[:3]
            top3_info = [
                (get_common_name(label), round(float(score) * 100, 1))
                for label, score in raw_scores_sorted
            ]
            chunk_str = f"Chunk {chunk_index}" if chunk_index is not None else "Chunk"
            logger.info(f"{chunk_str} raw model output", extra={
                'top3': top3_info,
                'cutoff': round(cutoff * 100, 1)
            })

        # Apply cutoff threshold
        scores = np.where(scores >= cutoff, scores, 0)

        # Build results dict, filter zeros, sort descending
        results_dict = dict(zip(labels, scores, strict=True))
        results_dict = {k: v for k, v in results_dict.items() if v != 0}
        return sorted(results_dict.items(), key=lambda x: x[1], reverse=True)

    def filter_by_location(self, lat: float, lon: float, week: int, threshold: float = DEFAULT_SPECIES_FILTER_THRESHOLD) -> list[str] | None:
        """Get species likely at a location during a specific week.

        Returns None if location filtering is not supported by this model.

        Deprecated: prefer the LocationFilter abstraction (location_filter.py)
        for new code. This method is retained for V2.4's embedded meta model.
        """
        return None
