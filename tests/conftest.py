# tests/conftest.py
import os, sys
# Ajoute la racine du repo au PYTHONPATH pour que "import api" fonctionne
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)