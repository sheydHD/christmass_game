# config.py

import os

# -------------------------------------------------------------------------
# GLOBAL CONFIG
# -------------------------------------------------------------------------
GRID_WIDTH = 48
GRID_HEIGHT = 27
TILE_SIZE = 32

PLAYER_SPEED = 2.0  # constant speed for all levels

DOOR_COLORS = {
    2: (139, 69, 19),   # Brown door
    3: (0,   128, 128), # Teal door
    4: (128, 0,   128), # Purple door
}

KEY_COLORS = {
    "key0": (255, 215, 0),   # Gold
    "key1": (0,   255, 255), # Cyan
    "key2": (255, 0,   255), # Magenta
}

WALL_COLOR = (0, 100, 0)
POINT_COLOR = (255, 255, 0)
FINISH_PORTAL_COLOR = (255, 0, 0)

LEVEL_BG_COLORS = {
    1: (180, 220, 255),
    2: (220, 220, 255),
    3: (210, 240, 210),
    4: (255, 240, 210),
    5: (200, 200, 200),
    6: (180, 180, 180),
}

ENEMY_COLOR = (200, 0, 0)

BUTTON_BG = (255, 255, 255)
BUTTON_TEXT = (0, 0, 0)
TEXT_COLOR = (255, 255, 255)

PROGRESS_FILE = "progress.json"

ROOM_COUNT = 5
MAX_ROOM_SIZE = 8
DOOR_COUNT = 3
POINT_COUNT = 6
MAX_LEVEL = 6

STATE_MENU = "menu"
STATE_GAME = "game"
STATE_OPTIONS = "options"
STATE_GAME_RULES = "gamerules"
STATE_LEVEL_SELECT = "levelselect"
STATE_INGAME_MENU = "ingame_menu"
STATE_END_LEVEL = "end_level"
STATE_USER_SELECT = "user_select"
STATE_NEW_USER = "new_user"

DISPLAY_MODES = ["maximized", "fullscreen"]  # no windowed

# used in user profiles
DEFAULT_DISPLAY_MODE = "maximized"
