import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def app(tmp_path):
    from app.config import Config
    Config.PAYMENTS_MODE = "mock"
    Config.DATA_DIR = str(tmp_path)
    Config.BASE_URL = "http://localhost:5000"
    from app.server import create_app
    a = create_app()
    a.config["TESTING"] = True
    return a


@pytest.fixture
def client(app):
    return app.test_client()


def sample_bytes(name):
    return open(os.path.join(ROOT, "samples", name), "rb").read()
