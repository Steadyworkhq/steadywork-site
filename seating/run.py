"""Local demo server: python run.py  ->  http://localhost:5000"""
import logging
from app.server import create_app

logging.basicConfig(level=logging.INFO)
app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
