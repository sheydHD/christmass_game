# profiles.py

import json
import os
from config import PROGRESS_FILE, MAX_LEVEL, DEFAULT_DISPLAY_MODE

def load_profiles():
    """Load the JSON containing multiple user profiles."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            data = json.load(f)
            if "profiles" not in data:
                data["profiles"] = {}
            return data
    return {"profiles": {}}

def save_profiles(data):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f)

def get_or_create_profile(data, username):
    """
    If username doesn't exist, create a default profile.
    Return the profile dict.
    """
    if username not in data["profiles"]:
        data["profiles"][username] = {
            "score": 0,
            "highest_unlocked_level": 1,
            "level_scores": [0]*(MAX_LEVEL+1),
            "display_mode": DEFAULT_DISPLAY_MODE
        }
    return data["profiles"][username]
