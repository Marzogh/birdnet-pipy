"""Tests for localized bird-name helpers."""

import importlib
import os
import tempfile
from unittest.mock import patch


class TestSpectrogramBirdNames:
    """Tests for spectrogram-safe bird name helpers."""

    def test_get_spectrogram_common_name_uses_localized_name_for_supported_scripts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            labels_dir = os.path.join(tmpdir, 'labels')
            os.makedirs(labels_dir)

            labels_en = os.path.join(labels_dir, 'BirdNET_GLOBAL_6K_V2.4_Labels_en.txt')
            labels_de = os.path.join(labels_dir, 'BirdNET_GLOBAL_6K_V2.4_Labels_de.txt')

            with open(labels_en, 'w', encoding='utf-8') as f:
                f.write('Turdus migratorius_American Robin\n')

            with open(labels_de, 'w', encoding='utf-8') as f:
                f.write('Turdus migratorius_Amsel\n')

            bird_name_utils = importlib.import_module('core.bird_name_utils')

            bird_name_utils.clear_bird_name_caches()
            try:
                with patch.object(bird_name_utils, 'LABELS_PATH', labels_en):
                    display_name = bird_name_utils.get_spectrogram_common_name(
                        'Turdus migratorius',
                        'American Robin',
                        settings={
                            'model': {'type': 'birdnet'},
                            'display': {'bird_name_language': 'de'},
                        },
                    )

                assert display_name == 'Amsel'
            finally:
                bird_name_utils.clear_bird_name_caches()

    def test_get_spectrogram_common_name_falls_back_to_english_for_unsupported_scripts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            labels_dir = os.path.join(tmpdir, 'labels')
            os.makedirs(labels_dir)

            labels_en = os.path.join(labels_dir, 'BirdNET_GLOBAL_6K_V2.4_Labels_en.txt')
            labels_ja = os.path.join(labels_dir, 'BirdNET_GLOBAL_6K_V2.4_Labels_ja.txt')

            with open(labels_en, 'w', encoding='utf-8') as f:
                f.write('Turdus migratorius_American Robin\n')

            with open(labels_ja, 'w', encoding='utf-8') as f:
                f.write('Turdus migratorius_アメリカンロビン\n')

            bird_name_utils = importlib.import_module('core.bird_name_utils')

            bird_name_utils.clear_bird_name_caches()
            try:
                with patch.object(bird_name_utils, 'LABELS_PATH', labels_en):
                    display_name = bird_name_utils.get_spectrogram_common_name(
                        'Turdus migratorius',
                        'American Robin',
                        settings={
                            'model': {'type': 'birdnet'},
                            'display': {'bird_name_language': 'ja'},
                        },
                    )
                    english_name = bird_name_utils.get_spectrogram_common_name_from_english(
                        'American Robin',
                        settings={
                            'model': {'type': 'birdnet'},
                            'display': {'bird_name_language': 'ja'},
                        },
                    )

                assert display_name == 'American Robin'
                assert english_name == 'American Robin'
            finally:
                bird_name_utils.clear_bird_name_caches()
