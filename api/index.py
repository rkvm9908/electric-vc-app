import sys
import os

# Make the project root importable (so `from models import ...`,
# `from routes...` work the same way they do locally)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app  # noqa: E402

# Vercel's Python runtime looks for a variable/callable named `app`