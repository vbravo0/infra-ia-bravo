"""Tests unitarios del pipeline de preparacion y limpieza de datos (REQ-05)."""

import pandas as pd
from train import clean_cve_dataset


def test_clean_cve_dataset_removes_nulls_in_description_and_severity():
    """Verifica que clean_cve_dataset descarte filas con NaN en DESCRIPTION o SEVERITY."""
    raw_data = {
        "CVE-ID": ["CVE-1", "CVE-2", "CVE-3", "CVE-4"],
        "DESCRIPTION": [
            "Valid description A",
            None,
            "Valid description C",
            "Valid description D",
        ],
        "SEVERITY": ["HIGH", "CRITICAL", None, "LOW"],
    }
    df = pd.DataFrame(raw_data)
    cleaned = clean_cve_dataset(df)

    assert len(cleaned) == 2
    assert set(cleaned["CVE-ID"]) == {"CVE-1", "CVE-4"}
    assert not cleaned["DESCRIPTION"].isna().any()
    assert not cleaned["SEVERITY"].isna().any()


def test_clean_cve_dataset_removes_duplicate_descriptions():
    """Verifica que clean_cve_dataset conserve solo una ocurrencia cuando hay descripciones identicas."""
    raw_data = {
        "CVE-ID": ["CVE-1", "CVE-2", "CVE-3"],
        "DESCRIPTION": [
            "Duplicated buffer overflow description in daemon",
            "Duplicated buffer overflow description in daemon",
            "Unique sql injection vulnerability in portal",
        ],
        "SEVERITY": ["HIGH", "HIGH", "CRITICAL"],
    }
    df = pd.DataFrame(raw_data)
    cleaned = clean_cve_dataset(df)

    assert len(cleaned) == 2
    assert cleaned["DESCRIPTION"].duplicated().sum() == 0
    assert "CVE-1" in cleaned["CVE-ID"].values
    assert "CVE-3" in cleaned["CVE-ID"].values
