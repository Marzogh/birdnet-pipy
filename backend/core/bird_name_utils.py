"""Helpers for localized bird display names."""

from __future__ import annotations

import os
from functools import lru_cache

from config.settings import LABELS_PATH, LABELS_V3_PATH
from core.runtime_config import get_runtime_settings
from model_service.label_utils import parse_v2_labels, parse_v3_labels

DEFAULT_BIRD_NAME_LANGUAGE = 'en'

BIRD_NAME_LANGUAGE_LABELS = {
    'af': 'Afrikaans',
    'ar': 'Arabic',
    'cs': 'Czech',
    'da': 'Danish',
    'de': 'German',
    'en': 'English (US)',
    'en_uk': 'English (UK)',
    'es': 'Spanish',
    'fi': 'Finnish',
    'fr': 'French',
    'hu': 'Hungarian',
    'it': 'Italian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'nl': 'Dutch',
    'no': 'Norwegian',
    'pl': 'Polish',
    'pt': 'Portuguese',
    'ro': 'Romanian',
    'ru': 'Russian',
    'sk': 'Slovak',
    'sl': 'Slovenian',
    'sv': 'Swedish',
    'th': 'Thai',
    'tr': 'Turkish',
    'uk': 'Ukrainian',
    'zh': 'Chinese',
}

SUPPORTED_BIRD_NAME_LANGUAGES = frozenset(BIRD_NAME_LANGUAGE_LABELS)
SPECTROGRAM_UNSUPPORTED_BIRD_NAME_LANGUAGES = frozenset({
    'ar',
    'ja',
    'ko',
    'th',
    'zh',
})
_V2_LABELS_PREFIX = 'BirdNET_GLOBAL_6K_V2.4_Labels_'
_V2_LABELS_SUFFIX = '.txt'


def normalize_bird_name_language(language: str | None) -> str:
    """Return a supported bird-name language code."""
    if language in SUPPORTED_BIRD_NAME_LANGUAGES:
        return language
    return DEFAULT_BIRD_NAME_LANGUAGE


def get_bird_name_language(settings: dict | None = None) -> str:
    """Read the preferred bird-name language from settings."""
    settings_data = settings or get_runtime_settings()
    display = settings_data.get('display', {})
    return normalize_bird_name_language(display.get('bird_name_language'))


def get_configured_model_type(settings: dict | None = None) -> str:
    """Read the configured model type from settings."""
    settings_data = settings or get_runtime_settings()
    return settings_data.get('model', {}).get('type', 'birdnet')


def _normalize_model_type(model_type: str | None) -> str:
    if model_type == 'birdnet_v3':
        return 'birdnet_v3'
    return 'birdnet'


def _get_v2_labels_path(language: str) -> str:
    return os.path.join(
        os.path.dirname(LABELS_PATH),
        f'{_V2_LABELS_PREFIX}{language}{_V2_LABELS_SUFFIX}',
    )


@lru_cache(maxsize=None)
def _load_model_labels(model_type: str, language: str) -> tuple[tuple[str, str], ...]:
    normalized_model_type = _normalize_model_type(model_type)
    normalized_language = normalize_bird_name_language(language)

    if normalized_model_type == 'birdnet_v3':
        return tuple(parse_v3_labels(LABELS_V3_PATH))

    labels_path = _get_v2_labels_path(normalized_language)
    if not os.path.exists(labels_path):
        labels_path = LABELS_PATH

    return tuple(parse_v2_labels(labels_path))


@lru_cache(maxsize=None)
def _get_scientific_to_localized_map(
    model_type: str,
    language: str,
) -> dict[str, str]:
    return {
        scientific_name: common_name
        for scientific_name, common_name in _load_model_labels(model_type, language)
    }


@lru_cache(maxsize=None)
def _get_english_to_localized_map(
    model_type: str,
    language: str,
) -> dict[str, str]:
    english_labels = _load_model_labels(model_type, DEFAULT_BIRD_NAME_LANGUAGE)
    localized_map = _get_scientific_to_localized_map(model_type, language)
    return {
        english_name: localized_map.get(scientific_name, english_name)
        for scientific_name, english_name in english_labels
    }


def clear_bird_name_caches() -> None:
    """Clear cached label mappings.

    Used by tests that swap label files.
    """
    _load_model_labels.cache_clear()
    _get_scientific_to_localized_map.cache_clear()
    _get_english_to_localized_map.cache_clear()


def get_localized_common_name(
    scientific_name: str | None,
    common_name: str | None = None,
    *,
    model_type: str | None = None,
    language: str | None = None,
    settings: dict | None = None,
) -> str:
    """Return a localized display name for a species."""
    resolved_settings = settings or get_runtime_settings()
    resolved_model_type = _normalize_model_type(model_type or get_configured_model_type(resolved_settings))
    resolved_language = normalize_bird_name_language(language or get_bird_name_language(resolved_settings))

    if scientific_name:
        localized = _get_scientific_to_localized_map(
            resolved_model_type,
            resolved_language,
        ).get(scientific_name)
        if localized:
            return localized

    return common_name or scientific_name or ''


def get_localized_common_name_from_english(
    common_name: str | None,
    *,
    model_type: str | None = None,
    language: str | None = None,
    settings: dict | None = None,
) -> str:
    """Return a localized display name when only the English common name is known."""
    if not common_name:
        return ''

    resolved_settings = settings or get_runtime_settings()
    resolved_model_type = _normalize_model_type(model_type or get_configured_model_type(resolved_settings))
    resolved_language = normalize_bird_name_language(language or get_bird_name_language(resolved_settings))

    return _get_english_to_localized_map(
        resolved_model_type,
        resolved_language,
    ).get(common_name, common_name)


def should_use_localized_spectrogram_titles(
    *,
    language: str | None = None,
    settings: dict | None = None,
) -> bool:
    """Return whether the bundled spectrogram font can safely render localized titles."""
    resolved_settings = settings or get_runtime_settings()
    resolved_language = normalize_bird_name_language(language or get_bird_name_language(resolved_settings))
    return resolved_language not in SPECTROGRAM_UNSUPPORTED_BIRD_NAME_LANGUAGES


def get_spectrogram_common_name(
    scientific_name: str | None,
    common_name: str | None = None,
    *,
    model_type: str | None = None,
    language: str | None = None,
    settings: dict | None = None,
) -> str:
    """Return the bird name to use in spectrogram titles."""
    resolved_settings = settings or get_runtime_settings()
    if not should_use_localized_spectrogram_titles(
        language=language,
        settings=resolved_settings,
    ):
        return common_name or scientific_name or ''

    return get_localized_common_name(
        scientific_name,
        common_name,
        model_type=model_type,
        language=language,
        settings=resolved_settings,
    )


def get_spectrogram_common_name_from_english(
    common_name: str | None,
    *,
    model_type: str | None = None,
    language: str | None = None,
    settings: dict | None = None,
) -> str:
    """Return the English or localized bird name to use in spectrogram titles."""
    resolved_settings = settings or get_runtime_settings()
    if not should_use_localized_spectrogram_titles(
        language=language,
        settings=resolved_settings,
    ):
        return common_name or ''

    return get_localized_common_name_from_english(
        common_name,
        model_type=model_type,
        language=language,
        settings=resolved_settings,
    )


def add_display_common_name(
    data: dict | None,
    *,
    model_type: str | None = None,
    language: str | None = None,
    settings: dict | None = None,
) -> dict | None:
    """Return a copy with display_common_name attached."""
    if not data:
        return data

    localized = get_localized_common_name(
        data.get('scientific_name'),
        data.get('common_name'),
        model_type=model_type,
        language=language,
        settings=settings,
    )

    enriched = dict(data)
    enriched['display_common_name'] = localized
    return enriched


def add_display_species(
    data: dict | None,
    *,
    model_type: str | None = None,
    language: str | None = None,
    settings: dict | None = None,
) -> dict | None:
    """Return a copy with displaySpecies attached."""
    if not data:
        return data

    localized = get_localized_common_name_from_english(
        data.get('species'),
        model_type=model_type,
        language=language,
        settings=settings,
    )

    enriched = dict(data)
    enriched['displaySpecies'] = localized
    return enriched
