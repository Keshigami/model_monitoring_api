import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
CHURN = HERE.parent / "churn_predictor"


@pytest.fixture(scope="session")
def client():
    """Train the churn bundle in its own venv if it is missing, then build a TestClient."""
    if not (CHURN / "models" / "churn.joblib").exists():
        subprocess.run(["uv", "run", "--project", str(CHURN), "python", "train.py"], cwd=CHURN, check=True)
    from fastapi.testclient import TestClient

    import main

    main.STATE.load()
    with TestClient(main.app) as c:
        yield c
