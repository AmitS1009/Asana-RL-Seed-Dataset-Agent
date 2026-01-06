from __future__ import annotations

from dataclasses import dataclass
import os
import random
from typing import Iterable

import requests


@dataclass(frozen=True)
class PublicCorpora:
    company_names: list[str]


def load_public_corpora(seed: int) -> PublicCorpora:
    rng = random.Random(seed)

    # Offline-safe defaults.
    company_names = [
        "AsterCloud",
        "Northwind Labs",
        "BluePeak Software",
        "HelioWorks",
        "QuantaFlow",
        "NimbusForge",
        "Vectorly",
        "CedarHQ",
        "PrismStack",
        "ArdentAI",
    ]

    if os.getenv("ENABLE_WEB_SCRAPE", "0").strip().lower() in {"1", "true", "yes", "y", "on"}:
        # Optional: fetch a small public list (best-effort). If it fails, fall back.
        try:
            url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            lines = resp.text.splitlines()[1:]
            for line in lines[:200]:
                name = line.split(",")[0].strip().strip('"')
                if name and name not in company_names:
                    company_names.append(name)
        except Exception:
            pass

    rng.shuffle(company_names)
    return PublicCorpora(company_names=company_names)
