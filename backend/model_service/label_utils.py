"""Utilities for parsing BirdNET label files.

These are kept free of ML dependencies so they can be imported
by both the model service and the API server.
"""

import csv


def parse_v2_labels(path: str) -> list[tuple[str, str]]:
    """Parse V2.4 text labels file.

    Text format: SciName_CommonName

    Returns:
        List of (scientific_name, common_name) tuples.
    """
    labels = []
    with open(path, encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            scientific_name, separator, common_name = line.partition('_')
            if scientific_name and separator and common_name:
                labels.append((scientific_name.strip(), common_name.strip()))

    return labels


def parse_v3_labels(path: str) -> list[tuple[str, str]]:
    """Parse V3.0 semicolon-delimited CSV labels file.

    CSV format: idx;id;sci_name;com_name;class;order

    Returns:
        List of (scientific_name, common_name) tuples.
    """
    labels = []
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            sci = row.get('sci_name', '').strip()
            com = row.get('com_name', '').strip()
            if sci and com:
                labels.append((sci, com))
    return labels
