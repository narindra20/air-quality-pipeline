import os
import sys
import json
import time
import logging
import datetime
from pathlib import Path
import requests

VILLES = [
    {"nom": "Paris", "lat": 48.8566, "lon": 2.3522},
    {"nom": "Marseille", "lat": 43.2965, "lon": 5.3698},
    {"nom": "Lyon", "lat": 45.7640, "lon": 4.8357},
    {"nom": "Toulouse", "lat": 43.6047, "lon": 1.4442},
    {"nom": "Nice", "lat": 43.7102, "lon": 7.2620}
]