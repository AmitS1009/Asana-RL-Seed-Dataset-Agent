from __future__ import annotations

import random
from faker import Faker


def build_rng(seed: int) -> random.Random:
    return random.Random(seed)


def build_faker(seed: int) -> Faker:
    fk = Faker()
    fk.seed_instance(seed)
    return fk
