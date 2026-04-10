"""Shared test fixtures.

Installs the project root on ``sys.path`` so tests can import ``terminal``
without installing the package. Provides a frozen config fixture and
synthetic data helpers.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from terminal.config_loader import load_config, reset_cache  # noqa: E402


@pytest.fixture(scope="session")
def config() -> dict:
    reset_cache()
    return load_config()


@pytest.fixture
def synthetic_prices() -> pd.Series:
    rng = np.random.default_rng(42)
    n = 400
    returns = rng.normal(0.0005, 0.01, n)
    prices = 100 * np.cumprod(1 + returns)
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    return pd.Series(prices, index=idx, name="close")


@pytest.fixture
def synthetic_returns_matrix() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    n, k = 500, 5
    data = rng.normal(0.0005, 0.01, (n, k))
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    return pd.DataFrame(data, index=idx, columns=[f"A{i}" for i in range(k)])
