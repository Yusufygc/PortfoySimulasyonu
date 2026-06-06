from __future__ import annotations

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import replicate_db


def test_make_db_url():
    env_data = {
        "DB_HOST": "localhost",
        "DB_PORT": "3306",
        "DB_USER": "root",
        "DB_PASSWORD": "secret_password",
        "DB_NAME": "my_db",
    }
    url = replicate_db.make_db_url(env_data)
    assert url == "mysql+mysqlconnector://root:secret_password@localhost:3306/my_db"


def test_make_db_url_raises_on_missing_fields():
    env_data = {
        "DB_HOST": "localhost",
        "DB_PORT": "3306",
        "DB_USER": "root",
        # DB_PASSWORD is missing
        "DB_NAME": "my_db",
    }
    with pytest.raises(SystemExit):
        replicate_db.make_db_url(env_data)


def test_main_aborts_when_db_credentials_match(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["replicate_db.py"])
    # Mock load_env_dict to return identical databases
    def mock_load_env(name):
        return {
            "DB_HOST": "localhost",
            "DB_PORT": "3306",
            "DB_USER": "root",
            "DB_PASSWORD": "pwd",
            "DB_NAME": "portfoySim",
        }

    monkeypatch.setattr(replicate_db, "load_env_dict", mock_load_env)
    
    # We expect sys.exit(1) due to identical DB config check
    with pytest.raises(SystemExit) as exc_info:
        replicate_db.main()
    
    assert exc_info.value.code == 1
