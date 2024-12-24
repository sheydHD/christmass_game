# Linux: pyinstaller --onefile --icon=game_icon.ico --add-data "sounds:sounds" main2.py
#
# Win: pyinstaller --onefile --icon=game_icon.ico --add-data "sounds;sounds" main2.py

import pygame
import sys
import random
import json
import os
import math
from collections import defaultdict, deque

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

DISPLAY_MODES = ["windowed", "maximized", "fullscreen"]

# -------------------------------------------------------------------------
# USER/PROFILE DATA
# -------------------------------------------------------------------------
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
    """If username doesn't exist, create a default profile."""
    if username not in data["profiles"]:
        data["profiles"][username] = {
            "score": 0,
            "highest_unlocked_level": 1,
            "level_scores": [0]*(MAX_LEVEL+1),
            "display_mode": "maximized"  # default
        }
    return data["profiles"][username]

# -------------------------------------------------------------------------
# MAZE GENERATION
# -------------------------------------------------------------------------
def generate_maze(width, height):
    maze = [[1 for _ in range(width)] for _ in range(height)]
    stack = [(1, 1)]
    maze[1][1] = 0
    directions = [(-1,0),(1,0),(0,-1),(0,1)]
    while stack:
        x,y = stack[-1]
        neighbors = []
        for dx,dy in directions:
            nx,ny = x+dx*2, y+dy*2
            if 0<nx<width-1 and 0<ny<height-1:
                if maze[ny][nx] == 1:
                    neighbors.append((nx,ny,dx,dy))
        if neighbors:
            nx,ny,dx,dy = random.choice(neighbors)
            maze[ny][nx] = 0
            maze[y+dy][x+dx] = 0
            stack.append((nx,ny))
        else:
            stack.pop()
    # border walls
    for i in range(width):
        maze[0][i] = 1
        maze[height-1][i] = 1
    for j in range(height):
        maze[j][0] = 1
        maze[j][width-1] = 1
    return maze

def carve_rooms(maze, room_count=ROOM_COUNT, max_room_size=MAX_ROOM_SIZE):
    h = len(maze)
    w = len(maze[0])
    for _ in range(room_count):
        rw = random.randint(3, max_room_size)
        rh = random.randint(3, max_room_size)
        x = random.randint(2, w-rw-2)
        y = random.randint(2, h-rh-2)
        for ry in range(y, y+rh):
            for rx in range(x, x+rw):
                maze[ry][rx] = 0

def place_doors(maze, door_count=DOOR_COUNT):
    door_vals = [2,3,4]
    random.shuffle(door_vals)
    h = len(maze)
    w = len(maze[0])
    placed = 0
    tries = 0
    while placed < door_count and tries < 1000:
        tries += 1
        xx = random.randint(2, w-3)
        yy = random.randint(2, h-3)
        if maze[yy][xx] == 0:
            maze[yy][xx] = door_vals[placed]
            placed += 1

def spawn_items(maze, count, item_type):
    items = []
    h = len(maze)
    w = len(maze[0])
    tries = 0
    while len(items) < count and tries < 5000:
        tries += 1
        tx = random.randint(1, w-2)
        ty = random.randint(1, h-2)
        if maze[ty][tx] == 0:
            px = tx*TILE_SIZE + TILE_SIZE//2
            py = ty*TILE_SIZE + TILE_SIZE//2
            items.append([px,py,item_type])
    return items

def spawn_keys(maze):
    all_keys = []
    for kt in ["key0","key1","key2"]:
        one = spawn_items(maze, 1, kt)
        all_keys.extend(one)
    return all_keys

def spawn_finish_portal(maze):
    tries = 0
    while tries < 5000:
        tries += 1
        tx = random.randint(1,GRID_WIDTH-2)
        ty = random.randint(1,GRID_HEIGHT-2)
        if maze[ty][tx] == 0:
            px = tx*TILE_SIZE + TILE_SIZE//2
            py = ty*TILE_SIZE + TILE_SIZE//2
            return [px,py,"finish_portal"]
    return None

# -------------------------------------------------------------------------
# BFS VALIDATION
# -------------------------------------------------------------------------
def can_pass_tile(tile_val, key_inv):
    """Return True if the tile can be passed normally by the player."""
    if tile_val == 1:
        return False
    elif tile_val in (2,3,4):
        needed_key = f"key{tile_val - 2}"
        return (key_inv[needed_key] > 0)
    else:
        return True

def is_level_valid(maze, items):
    """Check if the level is solvable: BFS with all keys & points & doors."""
    item_coords = []
    portal_coord = None
    for (px,py,typ) in items:
        tx = px//TILE_SIZE
        ty = py//TILE_SIZE
        item_coords.append((tx,ty,typ))
        if typ == "finish_portal":
            portal_coord = (tx,ty)

    from collections import deque
    visited = set()
    start = (1,1,0,0,0) # (x,y,key0,key1,key2)
    visited.add(start)
    queue = deque()
    queue.append(start)
    found_items = set()
    directions = [(-1,0),(1,0),(0,-1),(0,1)]

    while queue:
        cx,cy,k0,k1,k2 = queue.popleft()
        # check items
        for (ix,iy,typ) in item_coords:
            if (ix,iy) == (cx,cy) and (ix,iy) not in found_items:
                found_items.add((ix,iy))
                nk0,nk1,nk2 = k0,k1,k2
                if typ.startswith("key"):
                    if typ=="key0": nk0=1
                    if typ=="key1": nk1=1
                    if typ=="key2": nk2=1
                new_st = (cx,cy,nk0,nk1,nk2)
                if new_st not in visited:
                    visited.add(new_st)
                    queue.append(new_st)

        # BFS expansions
        keys_dict = {"key0":k0,"key1":k1,"key2":k2}
        for dx,dy in directions:
            nx,ny = cx+dx, cy+dy
            if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                tile_val = maze[ny][nx]
                if can_pass_tile(tile_val, keys_dict):
                    st = (nx,ny,k0,k1,k2)
                    if st not in visited:
                        visited.add(st)
                        queue.append(st)

    # check if all items (point/key) are found
    for (ix,iy,typ) in item_coords:
        if typ in ("point","key0","key1","key2") and (ix,iy) not in found_items:
            return False

    # check if finish portal is reachable
    if portal_coord:
        px,py = portal_coord
        if not any((px,py,a,b,c) in visited for a in [0,1] for b in [0,1] for c in [0,1]):
            return False

    # ensure all floor tiles visited
    for yy in range(GRID_HEIGHT):
        for xx in range(GRID_WIDTH):
            if maze[yy][xx] == 0:
                if not any((xx,yy,a,b,c) in visited for a in [0,1] for b in [0,1] for c in [0,1]):
                    return False

    return True

def create_level_until_valid(level):
    """Generate a random maze + items that is guaranteed solvable."""
    while True:
        maze = generate_maze(GRID_WIDTH,GRID_HEIGHT)
        carve_rooms(maze)
        if maze[1][1] == 1:
            continue
        items = []
        if level >= 2:
            place_doors(maze)
            keys_ = spawn_keys(maze)
            pts_ = spawn_items(maze, POINT_COUNT, "point")
            items = keys_ + pts_
        else:
            pts_ = spawn_items(maze, POINT_COUNT, "point")
            items = pts_

        finish_p = spawn_finish_portal(maze)
        if finish_p:
            items.append(finish_p)

        if is_level_valid(maze, items):
            return maze, items

# -------------------------------------------------------------------------
# ENEMIES
# -------------------------------------------------------------------------
def spawn_enemies_for_level(maze, level):
    """Spawn 'level' enemies for level >=3."""
    if level < 3:
        return []
    count = level
    enemies = []
    h = len(maze)
    w = len(maze[0])
    tries = 0
    while len(enemies) < count and tries < 3000:
        tries += 1
        tx = random.randint(1,w-2)
        ty = random.randint(1,h-2)
        if maze[ty][tx] == 0:
            ex = tx*TILE_SIZE + TILE_SIZE//2
            ey = ty*TILE_SIZE + TILE_SIZE//2
            dx = random.choice([-1,0,1])
            dy = random.choice([-1,0,1])
            if dx==0 and dy==0:
                dx=1
            enemies.append({
                'x':ex,'y':ey,
                'dx':dx,'dy':dy,
                'dir_change_cooldown':random.uniform(1.0,3.0)
            })
    return enemies

def move_enemies(enemies, dt):
    """Simple wandering movement for enemies."""
    sp = PLAYER_SPEED*TILE_SIZE*0.5
    for e in enemies:
        e['dir_change_cooldown'] -= dt
        if e['dir_change_cooldown'] <= 0:
            e['dx'] = random.choice([-1,0,1])
            e['dy'] = random.choice([-1,0,1])
            if e['dx']==0 and e['dy']==0:
                e['dx']=1
            e['dir_change_cooldown'] = random.uniform(1.0,3.0)

        e['x'] += e['dx']*sp*dt
        e['y'] += e['dy']*sp*dt

        # keep them in-bounds
        if e['x'] < 0:
            e['x'] = 0
            e['dx'] = random.choice([-1,0,1])
        elif e['x'] > GRID_WIDTH*TILE_SIZE:
            e['x'] = GRID_WIDTH*TILE_SIZE
            e['dx'] = random.choice([-1,0,1])
        if e['y'] < 0:
            e['y'] = 0
            e['dy'] = random.choice([-1,0,1])
        elif e['y'] > GRID_HEIGHT*TILE_SIZE:
            e['y'] = GRID_HEIGHT*TILE_SIZE
            e['dy'] = random.choice([-1,0,1])

def check_enemy_collision(px,py,enemies):
    for e in enemies:
        ex,ey = e['x'], e['y']
        dist_sq = (px-ex)**2 + (py-ey)**2
        if dist_sq < (TILE_SIZE//2)**2:
            return True
    return False

# -------------------------------------------------------------------------
def update_fog_of_war_permanent(discovered, px, py, radius=5):
    tile_x = int(px//TILE_SIZE)
    tile_y = int(py//TILE_SIZE)
    for yy in range(tile_y-radius, tile_y+radius+1):
        for xx in range(tile_x-radius, tile_x+radius+1):
            if 0 <= xx < GRID_WIDTH and 0 <= yy < GRID_HEIGHT:
                dist_sq = (xx - tile_x)**2 + (yy - tile_y)**2
                if dist_sq <= radius**2:
                    discovered[yy][xx] = True

def update_fog_of_war_ephemeral(px, py, radius=5):
    tile_x = int(px//TILE_SIZE)
    tile_y = int(py//TILE_SIZE)
    ephemeral = [[False for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
    for yy in range(tile_y-radius, tile_y+radius+1):
        for xx in range(tile_x-radius, tile_x+radius+1):
            if 0 <= xx < GRID_WIDTH and 0 <= yy < GRID_HEIGHT:
                dist_sq = (xx - tile_x)**2 + (yy - tile_y)**2
                if dist_sq <= radius**2:
                    ephemeral[yy][xx] = True
    return ephemeral

# -------------------------------------------------------------------------
def setup_level(level):
    maze, items = create_level_until_valid(level)
    en = spawn_enemies_for_level(maze, level)
    bg_color = LEVEL_BG_COLORS.get(level, (100,100,100))
    fog_discovered = None
    if level==5 or level==6:
        fog_discovered=[[False for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

    # count how many points & keys are in this level
    points_in_level = sum(1 for i in items if i[2]=="point")
    keys_in_level   = sum(1 for i in items if i[2].startswith("key"))

    return maze, items, bg_color, en, fog_discovered, points_in_level, keys_in_level

def draw_player_as_triangle(screen, x, y, direction_degs):
    size = int(TILE_SIZE*0.7)
    half = size//2
    local_points = [
        (half,0),
        (-half,int(0.6*half)),
        (-half,-int(0.6*half)),
    ]
    rad = math.radians(direction_degs)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    rotated = []
    for lx,ly in local_points:
        rx = lx*cos_a - ly*sin_a
        ry = lx*sin_a + ly*cos_a
        rotated.append((x+rx, y+ry))
    pygame.draw.polygon(screen, (255,0,0), rotated)

def draw_button(screen, rect, text, font,
                bg_color=BUTTON_BG, text_color=BUTTON_TEXT,
                click_sound=None):
    mx, my = pygame.mouse.get_pos()
    hovered = rect.collidepoint(mx, my)
    if hovered:
        use_bg = text_color
        use_text = bg_color
    else:
        use_bg = bg_color
        use_text = text_color

    pygame.draw.rect(screen, use_bg, rect)
    lbl = font.render(text, True, use_text)
    lbl_rect = lbl.get_rect(center=rect.center)
    screen.blit(lbl, lbl_rect)

# -------------------------------------------------------------------------
def main():
    pygame.init()          # <-- Add this line
    pygame.mixer.init()

    def resource_path(relative_path):
        """Get the absolute path to a resource, works for PyInstaller."""
        if getattr(sys, 'frozen', False):  # Check if running as a PyInstaller bundle
            base_path = sys._MEIPASS  # Temporary folder where PyInstaller unpacks files
        else:
            base_path = os.path.abspath(".")  # Running as a script
        return os.path.join(base_path, relative_path)

    # Update SOUNDS_PATH to use resource_path
    SOUNDS_PATH = resource_path("sounds/")

    # Music placeholders
    MENU_MUSIC = resource_path(SOUNDS_PATH + "your_menu_music.ogg")
    LEVEL_MUSIC = {
        1: resource_path(SOUNDS_PATH + "your_level1_music.ogg"),
        2: resource_path(SOUNDS_PATH + "your_level1_music.ogg"),
        3: resource_path(SOUNDS_PATH + "your_level1_music.ogg"),
        4: resource_path(SOUNDS_PATH + "your_level1_music.ogg"),
        5: resource_path(SOUNDS_PATH + "your_level1_music.ogg"),
        6: resource_path(SOUNDS_PATH + "your_level1_music.ogg"),
    }

    # Sound effects
    SFX_COIN = resource_path(SOUNDS_PATH + "your_coin_sound.ogg")
    SFX_BUTTON = resource_path(SOUNDS_PATH + "your_button_click.ogg")
    SFX_ENEMY_HIT = resource_path(SOUNDS_PATH + "your_enemy_touch.ogg")
    SFX_LEVEL_FIN = resource_path(SOUNDS_PATH + "your_finish_sound.ogg")
    SFX_LEVEL_START = resource_path(SOUNDS_PATH + "your_level_start.ogg")

    # Preload sounds if you want:
    coin_sound       = pygame.mixer.Sound(SFX_COIN)
    button_sound     = pygame.mixer.Sound(SFX_BUTTON)
    enemy_hit_sound  = pygame.mixer.Sound(SFX_ENEMY_HIT)
    level_finish_sound = pygame.mixer.Sound(SFX_LEVEL_FIN)
    level_start_sound = pygame.mixer.Sound(SFX_LEVEL_START)

    # A helper to start music
    def play_music(music_file, loop=-1, volume=1.0):
        pygame.mixer.music.load(music_file)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(loop)

    # A helper to stop music
    def stop_music():
        pygame.mixer.music.stop()

    # We’ll keep track of whether we’re currently playing level music or menu music, etc.
    # For simplicity, we’ll call play_music() at the right times in game_state transitions.

    data = load_profiles()

    current_user = None
    profile = None

    def apply_display_mode(mode):
        nonlocal screen
        if mode=="fullscreen":
            screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
        elif mode=="maximized":
            info = pygame.display.Info()
            w,h = info.current_w, info.current_h
            screen = pygame.display.set_mode((w,h), pygame.RESIZABLE)
        else:
            screen = pygame.display.set_mode((1280,720), pygame.RESIZABLE)

    def switch_user(username):
        nonlocal current_user, profile
        current_user = username
        profile = get_or_create_profile(data, username)
        apply_display_mode(profile.get("display_mode","maximized"))

    if len(data["profiles"])>0:
        first_user = list(data["profiles"].keys())[0]
        switch_user(first_user)
    else:
        current_user = None
        profile = None
        screen = pygame.display.set_mode((1280,720), pygame.RESIZABLE)

    # Start with menu music
    play_music(MENU_MUSIC)

    game_state = STATE_MENU

    def get_highest_unlocked_level():
        return profile["highest_unlocked_level"]
    def set_highest_unlocked_level(l):
        profile["highest_unlocked_level"] = l
    def get_level_score(lvl):
        return profile["level_scores"][lvl]
    def add_level_score(lvl, amount):
        profile["level_scores"][lvl]+=amount

    current_level = 1
    game_finished = False

    maze = []
    items = []
    background_color = (50,50,50)
    enemies = []
    fog_discovered = None

    points_in_level = 0
    keys_in_level   = 0
    points_collected= 0
    keys_collected  = 0

    key_inventory = defaultdict(int)

    # ---------------------------------------------------------------------
    # GHOST SKILL (Space)
    # ---------------------------------------------------------------------
    ghost_skill_active = False
    ghost_skill_timer = 0.0
    ghost_skill_cooldown = 0.0
    ghost_skill_uses_left = 3
    ghost_skill_max_uses = 3
    ghost_skill_wall_passed = False  # only 1 wall per activation

    # ---------------------------------------------------------------------
    # REVEAL SKILL (Q)
    # ---------------------------------------------------------------------
    reveal_skill_active = False
    reveal_skill_timer = 0.0
    reveal_skill_cooldown = 0.0

    ephemeral_fog = None

    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 32)

    new_user_text=""
    user_message=""

    BUTTON_WIDTH = 220
    BUTTON_HEIGHT = 50
    BUTTON_SPACING = 10
    def layout_menu_buttons(labels):
        sw = screen.get_width()
        sh = screen.get_height()
        total_height = len(labels)*(BUTTON_HEIGHT+BUTTON_SPACING)
        start_y = (sh - total_height)//2
        result = []
        for i, txt in enumerate(labels):
            rect = pygame.Rect(0,0,BUTTON_WIDTH,BUTTON_HEIGHT)
            rect.centerx = sw//2
            rect.y = start_y + i*(BUTTON_HEIGHT+BUTTON_SPACING)
            result.append((txt, rect))
        return result

    def reset_level(lvl):
        """Reset all data for the given level, including skill usage."""
        nonlocal maze, items, background_color, enemies, fog_discovered
        nonlocal player_x, player_y, direction_degs, key_inventory, game_finished, ephemeral_fog
        nonlocal points_in_level, keys_in_level, points_collected, keys_collected
        nonlocal ghost_skill_active, ghost_skill_timer, ghost_skill_cooldown
        nonlocal ghost_skill_uses_left, ghost_skill_wall_passed
        nonlocal reveal_skill_active, reveal_skill_timer, reveal_skill_cooldown

        game_finished=False
        direction_degs=0.0
        key_inventory=defaultdict(int)
        ephemeral_fog=None

        ghost_skill_active = False
        ghost_skill_timer = 0.0
        ghost_skill_cooldown = 0.0
        ghost_skill_uses_left = ghost_skill_max_uses
        ghost_skill_wall_passed = False

        reveal_skill_active = False
        reveal_skill_timer = 0.0
        reveal_skill_cooldown = 0.0

        m, its, bg, en, fd, p_cnt, k_cnt = setup_level(lvl)
        maze = m
        items = its
        background_color = bg
        enemies = en
        fog_discovered = fd
        points_in_level = p_cnt
        keys_in_level   = k_cnt
        points_collected= 0
        keys_collected  = 0

        player_x = TILE_SIZE + TILE_SIZE//2
        player_y = TILE_SIZE + TILE_SIZE//2

    def go_to_level(lvl):
        nonlocal current_level, game_state
        current_level = lvl
        reset_level(lvl)
        game_state = STATE_GAME

        # Stop the menu music and play the level's music
        stop_music()
        if lvl in LEVEL_MUSIC:
            play_music(LEVEL_MUSIC[lvl], loop=-1, volume=1.0)
        else:
            # If you want a fallback music or silence, handle it here
            pass

        # Optionally play a "level start" sound effect
        level_start_sound.play()

    player_x = player_y = 0
    direction_degs = 0.0

    now_time = pygame.time.get_ticks()/1000.0
    prev_time = now_time
    running = True

    while running:
        now_time = pygame.time.get_ticks()/1000.0
        dt = now_time - prev_time
        prev_time = now_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running=False
            elif event.type == pygame.VIDEORESIZE:
                pass
            elif event.type == pygame.KEYDOWN:
                if game_state == STATE_NEW_USER:
                    if event.key == pygame.K_BACKSPACE and len(new_user_text)>0:
                        new_user_text = new_user_text[:-1]
                    elif event.key == pygame.K_RETURN:
                        if new_user_text.strip():
                            if new_user_text in data["profiles"]:
                                user_message="Username already exists!"
                            else:
                                switch_user(new_user_text.strip())
                                user_message="User created!"
                                game_state=STATE_MENU
                                save_profiles(data)
                    else:
                        if len(new_user_text)<20 and event.unicode.isprintable():
                            new_user_text += event.unicode

                elif game_state == STATE_GAME:
                    # Ghost Skill (Space)
                    if event.key == pygame.K_SPACE:
                        if (not ghost_skill_active
                            and ghost_skill_cooldown <= 0
                            and ghost_skill_uses_left > 0):
                            # Check border:
                            tile_x = int(player_x // TILE_SIZE)
                            tile_y = int(player_y // TILE_SIZE)
                            if (tile_x <= 0 or tile_x >= GRID_WIDTH-1
                                or tile_y <= 0 or tile_y >= GRID_HEIGHT-1):
                                print("Cannot use ghost skill at the border!")
                            else:
                                ghost_skill_active = True
                                ghost_skill_timer = 2.0
                                ghost_skill_cooldown = 15.0
                                ghost_skill_uses_left -= 1
                                ghost_skill_wall_passed = False

                    # Reveal Skill (Q)
                    elif event.key == pygame.K_q:
                        if (not reveal_skill_active
                            and reveal_skill_cooldown <= 0):
                            reveal_skill_active = True
                            reveal_skill_timer = 5.0
                            reveal_skill_cooldown = 20.0

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mx,my = event.pos
                    # --------------- MENUS ETC ---------------
                    if game_state == STATE_MENU:
                        if profile:
                            menu_labels = ["Start Game","Select Level","Options","Game Rules","Exit","Switch User"]
                            menu_buttons = layout_menu_buttons(menu_labels)
                            for label, rect in menu_buttons:
                                if rect.collidepoint(mx,my):
                                    # Play button click sound
                                    button_sound.play()

                                    if label == "Start Game":
                                        go_to_level(profile["highest_unlocked_level"])
                                    elif label == "Select Level":
                                        game_state = STATE_LEVEL_SELECT
                                    elif label == "Options":
                                        game_state = STATE_OPTIONS
                                    elif label == "Game Rules":
                                        game_state = STATE_GAME_RULES
                                    elif label == "Exit":
                                        running=False
                                    elif label == "Switch User":
                                        game_state=STATE_USER_SELECT
                                    break
                        else:
                            # If no profile, go to user select
                            game_state=STATE_USER_SELECT

                    elif game_state == STATE_LEVEL_SELECT:
                        back_rect = pygame.Rect(20,20,100,40)
                        if back_rect.collidepoint(mx,my):
                            button_sound.play()
                            game_state = STATE_MENU
                        else:
                            labels = [f"Level {l}" for l in range(1,MAX_LEVEL+1)]
                            lvl_buttons = layout_menu_buttons(labels)
                            hul = profile["highest_unlocked_level"] if profile else 1
                            for i, (lbl, rct) in enumerate(lvl_buttons, start=1):
                                if rct.collidepoint(mx,my):
                                    button_sound.play()
                                    if i <= hul:
                                        go_to_level(i)
                                    break

                    elif game_state == STATE_OPTIONS:
                        back_rect = pygame.Rect(20,20,100,40)
                        if back_rect.collidepoint(mx,my):
                            button_sound.play()
                            game_state = STATE_MENU
                        else:
                            labels = ["Display Mode","Reset Stats","Full Screen","Back To Menu"]
                            opts_buttons = layout_menu_buttons(labels)
                            for label, rct in opts_buttons:
                                if rct.collidepoint(mx,my):
                                    button_sound.play()
                                    if label=="Display Mode":
                                        current_mode = profile.get("display_mode","maximized")
                                        idx = DISPLAY_MODES.index(current_mode)
                                        idx = (idx+1)%len(DISPLAY_MODES)
                                        new_mode = DISPLAY_MODES[idx]
                                        profile["display_mode"] = new_mode
                                        apply_display_mode(new_mode)
                                        save_profiles(data)
                                    elif label=="Reset Stats":
                                        profile["score"] = 0
                                        profile["highest_unlocked_level"] = 1
                                        profile["level_scores"] = [0]*(MAX_LEVEL+1)
                                        save_profiles(data)
                                    elif label=="Full Screen":
                                        profile["display_mode"] = "fullscreen"
                                        apply_display_mode("fullscreen")
                                        save_profiles(data)
                                    elif label=="Back To Menu":
                                        game_state=STATE_MENU
                                    break

                    elif game_state == STATE_GAME_RULES:
                        back_rect = pygame.Rect(20,20,100,40)
                        if back_rect.collidepoint(mx,my):
                            button_sound.play()
                            game_state=STATE_MENU

                    elif game_state == STATE_GAME:
                        menu_button_rect = pygame.Rect(10,10,80,40)
                        if menu_button_rect.collidepoint(mx,my):
                            button_sound.play()
                            game_state=STATE_INGAME_MENU

                    elif game_state == STATE_INGAME_MENU:
                        labels = ["Resume","Reset Level","Select Level","Options","Exit"]
                        ingame_buttons = layout_menu_buttons(labels)
                        for label, rct in ingame_buttons:
                            if rct.collidepoint(mx,my):
                                button_sound.play()
                                if label=="Resume":
                                    game_state=STATE_GAME
                                elif label=="Reset Level":
                                    reset_level(current_level)
                                    game_state=STATE_GAME
                                elif label=="Select Level":
                                    game_state=STATE_LEVEL_SELECT
                                elif label=="Options":
                                    game_state=STATE_OPTIONS
                                elif label=="Exit":
                                    running=False
                                break

                    elif game_state == STATE_USER_SELECT:
                        back_rect = pygame.Rect(20,20,100,40)
                        if back_rect.collidepoint(mx,my):
                            button_sound.play()
                            game_state=STATE_MENU
                        else:
                            labels = ["New User"]
                            user_buttons = layout_menu_buttons(labels)
                            clicked_new_user=False
                            for (lbl, rct) in user_buttons:
                                if rct.collidepoint(mx,my):
                                    button_sound.play()
                                    if lbl=="New User":
                                        game_state=STATE_NEW_USER
                                        clicked_new_user=True
                                    break
                            if not clicked_new_user:
                                yy = 200
                                for usr in data["profiles"]:
                                    r=pygame.Rect(0,0,200,40)
                                    r.centerx=screen.get_width()//2
                                    r.y=yy
                                    yy+=50
                                    if r.collidepoint(mx,my):
                                        button_sound.play()
                                        switch_user(usr)
                                        save_profiles(data)
                                        game_state=STATE_MENU
                                        break

                    elif game_state==STATE_NEW_USER:
                        create_rect = pygame.Rect(0,0,150,40)
                        create_rect.center = (screen.get_width()//2, 250)
                        if create_rect.collidepoint(mx,my):
                            button_sound.play()
                            if new_user_text.strip():
                                if new_user_text in data["profiles"]:
                                    user_message="Username already exists!"
                                else:
                                    switch_user(new_user_text.strip())
                                    user_message="User created!"
                                    game_state=STATE_MENU
                                    save_profiles(data)

                    elif game_state == STATE_END_LEVEL:
                        labels = ["Next Level","Menu"]
                        endlevel_buttons = layout_menu_buttons(labels)
                        for label, rct in endlevel_buttons:
                            if rct.collidepoint(mx,my):
                                button_sound.play()
                                if label=="Next Level":
                                    if current_level < MAX_LEVEL:
                                        go_to_level(current_level+1)
                                    else:
                                        game_state=STATE_MENU
                                        # Switch back to menu music
                                        stop_music()
                                        play_music(MENU_MUSIC)
                                elif label=="Menu":
                                    game_state=STATE_MENU
                                    # Switch back to menu music
                                    stop_music()
                                    play_music(MENU_MUSIC)
                                break

        # -------------------------------
        # GAME UPDATES
        # -------------------------------
        if game_state == STATE_GAME and profile:
            # 1) Update skill timers
            if ghost_skill_cooldown>0:
                ghost_skill_cooldown-=dt
                if ghost_skill_cooldown<0:
                    ghost_skill_cooldown=0

            if ghost_skill_active:
                ghost_skill_timer-=dt
                if ghost_skill_timer<=0:
                    # skill ended
                    ghost_skill_active=False
                    # If inside a wall, push out:
                    tile_x=int(player_x//TILE_SIZE)
                    tile_y=int(player_y//TILE_SIZE)
                    if 0<=tile_x<GRID_WIDTH and 0<=tile_y<GRID_HEIGHT:
                        if maze[tile_y][tile_x] == 1:
                            player_x = old_px
                            player_y = old_py
                    ghost_skill_wall_passed=False

            # Reveal skill
            if reveal_skill_cooldown>0:
                reveal_skill_cooldown-=dt
                if reveal_skill_cooldown<0:
                    reveal_skill_cooldown=0

            if reveal_skill_active:
                reveal_skill_timer-=dt
                if reveal_skill_timer<=0:
                    reveal_skill_active=False

            # 2) Handle movement with diagonal fix (two-step)
            keys = pygame.key.get_pressed()
            vel_x = 0
            vel_y = 0
            if keys[pygame.K_w]:
                vel_y=-PLAYER_SPEED
            if keys[pygame.K_s]:
                vel_y=PLAYER_SPEED
            if keys[pygame.K_a]:
                vel_x=-PLAYER_SPEED
            if keys[pygame.K_d]:
                vel_x=PLAYER_SPEED

            if abs(vel_x)>0.01 or abs(vel_y)>0.01:
                direction_degs = math.degrees(math.atan2(vel_y,vel_x))

            old_px=player_x
            old_py=player_y

            # First move in X
            temp_x = player_x + vel_x
            temp_y = player_y
            tx=int(temp_x//TILE_SIZE)
            ty=int(temp_y//TILE_SIZE)

            def tile_passable(tx, ty):
                """Returns True if (tx, ty) is passable given the keys and ghost skill."""
                if not (0 <= tx < GRID_WIDTH and 0 <= ty < GRID_HEIGHT):
                    return False
                tile_val = maze[ty][tx]
                if tile_val == 0:  # floor
                    return True
                elif tile_val in (2,3,4):  # door
                    needed_key = f"key{tile_val - 2}"
                    return (key_inventory[needed_key] > 0)
                elif tile_val == 1:  # wall
                    # disallow if it's the outermost wall
                    if tx in (0, GRID_WIDTH-1) or ty in (0, GRID_HEIGHT-1):
                        return False
                    # ghost skill?
                    if ghost_skill_active and not ghost_skill_wall_passed:
                        return True
                    return False
                else:
                    return True

            # move x
            if 0<=tx<GRID_WIDTH and 0<=ty<GRID_HEIGHT:
                if tile_passable(tx,ty):
                    if maze[ty][tx] == 1 and ghost_skill_active and not ghost_skill_wall_passed:
                        ghost_skill_wall_passed = True
                    player_x = temp_x

            # move y
            temp_x = player_x
            temp_y = player_y + vel_y
            tx=int(temp_x//TILE_SIZE)
            ty=int(temp_y//TILE_SIZE)
            if 0<=tx<GRID_WIDTH and 0<=ty<GRID_HEIGHT:
                if tile_passable(tx,ty):
                    if maze[ty][tx] == 1 and ghost_skill_active and not ghost_skill_wall_passed:
                        ghost_skill_wall_passed = True
                    player_y = temp_y

            # 3) Enemies
            move_enemies(enemies, dt)
            if check_enemy_collision(player_x, player_y, enemies):
                # If the enemy touches the player
                enemy_hit_sound.play()
                reset_level(current_level)
                continue

            # 4) Item pickup
            for it in items[:]:
                ix,iy,typ = it
                dist_sq = (player_x-ix)**2 + (player_y-iy)**2
                if dist_sq < (TILE_SIZE//2)**2:
                    if typ=="point":
                        # coin/point pickup
                        coin_sound.play()
                        items.remove(it)
                        points_collected += 1
                    elif typ.startswith("key"):
                        # key pickup
                        coin_sound.play()  # or some other key pickup sound
                        items.remove(it)
                        keys_collected += 1
                        key_inventory[typ]+=1
                    elif typ=="finish_portal":
                        # only pick up if all points are collected
                        if points_collected >= points_in_level:
                            # finishing level
                            level_finish_sound.play()
                            items.remove(it)
                            game_state=STATE_END_LEVEL
                            # Switch back to menu music or show scoreboard first
                            # (We've set game_state to STATE_END_LEVEL to handle UI)

            # 5) Fog
            if current_level==5 and fog_discovered:
                update_fog_of_war_permanent(fog_discovered,player_x,player_y,5)
            elif current_level==6:
                ephemeral_fog=update_fog_of_war_ephemeral(player_x,player_y,5)

        # ----------------------------------------------
        # RENDER
        # ----------------------------------------------
        screen.fill((20,20,20))
        if game_state==STATE_MENU:
            if profile:
                menu_labels = ["Start Game","Select Level","Options","Game Rules","Exit","Switch User"]
            else:
                menu_labels = ["Switch User"]

            title_txt = font.render("MAIN MENU", True, (255,255,255))
            title_rect = title_txt.get_rect(center=(screen.get_width()//2, 80))
            screen.blit(title_txt, title_rect)

            user_str = f"Current user: {current_user if current_user else 'None'}"
            user_txt = font.render(user_str, True, (255,255,255))
            user_rect = user_txt.get_rect(center=(screen.get_width()//2, 130))
            screen.blit(user_txt, user_rect)

            menu_buttons = layout_menu_buttons(menu_labels)
            for label, rect in menu_buttons:
                draw_button(screen, rect, label, font)

        elif game_state==STATE_LEVEL_SELECT:
            back_rect = pygame.Rect(20,20,100,40)
            draw_button(screen, back_rect, "Back", font)

            t=font.render("Select Level:",True,(255,255,255))
            screen.blit(t,(50,80))

            labels = [f"Level {l}" for l in range(1,MAX_LEVEL+1)]
            lvl_buttons = layout_menu_buttons(labels)
            hul = profile["highest_unlocked_level"] if profile else 1
            for i, (lbl, rct) in enumerate(lvl_buttons, start=1):
                if i<=hul:
                    draw_button(screen, rct, lbl, font)
                else:
                    pygame.draw.rect(screen,(150,150,150), rct)
                    s=font.render(lbl, True, (80,80,80))
                    s_rect=s.get_rect(center=rct.center)
                    screen.blit(s, s_rect)

        elif game_state==STATE_OPTIONS:
            back_rect = pygame.Rect(20,20,100,40)
            draw_button(screen, back_rect,"Back",font)

            labels = ["Display Mode","Reset Stats","Full Screen","Back To Menu"]
            opts_buttons = layout_menu_buttons(labels)

            mode_txt = profile.get("display_mode","maximized") if profile else "maximized"
            m_surf = font.render(f"Current Mode: {mode_txt}",True,(255,255,255))
            screen.blit(m_surf,(screen.get_width()//2 - m_surf.get_width()//2, 150))

            for label, rct in opts_buttons:
                draw_button(screen, rct, label, font)

        elif game_state==STATE_GAME_RULES:
            back_rect = pygame.Rect(20,20,100,40)
            draw_button(screen, back_rect,"Back", font)

            lines=[
                "GAME RULES:",
                "- Move with W/A/S/D.",
                "- Collect ALL points before the finish portal is usable.",
                "- Keys open colored doors.",
                "- Fog: L5 = permanent, L6 = ephemeral.",
                "- Space (Ghost): 2s, pass 1 wall; 15s cooldown, 3 uses per level.",
                "- Q (Reveal): show coins/keys for 5s; 20s cooldown.",
                "- Can't use Ghost skill on the border; if skill ends in a wall, you get pushed out.",
                "- Press 'Menu' in top-left for in-game menu.",
            ]
            yy=80
            for l in lines:
                r=font.render(l,True,(255,255,255))
                screen.blit(r,(50,yy))
                yy+=40

        elif game_state==STATE_GAME:
            offset_x=(screen.get_width()-GRID_WIDTH*TILE_SIZE)//2
            offset_y=(screen.get_height()-GRID_HEIGHT*TILE_SIZE)//2
            pygame.draw.rect(screen, background_color,
                             (offset_x, offset_y, GRID_WIDTH*TILE_SIZE, GRID_HEIGHT*TILE_SIZE))

            # Draw Maze
            for yy in range(GRID_HEIGHT):
                for xx in range(GRID_WIDTH):
                    tile_val=maze[yy][xx]
                    rx=offset_x + xx*TILE_SIZE
                    ry=offset_y + yy*TILE_SIZE
                    # Fog check
                    visible=True
                    if not reveal_skill_active: 
                        if current_level==5:
                            if fog_discovered and not fog_discovered[yy][xx]:
                                visible=False
                        elif current_level==6:
                            if ephemeral_fog and not ephemeral_fog[yy][xx]:
                                visible=False
                    if not visible:
                        pygame.draw.rect(screen,(0,0,0),(rx,ry,TILE_SIZE,TILE_SIZE))
                        continue

                    if tile_val==1:
                        pygame.draw.rect(screen,WALL_COLOR,(rx,ry,TILE_SIZE,TILE_SIZE))
                    elif tile_val in (2,3,4):
                        pygame.draw.rect(screen,DOOR_COLORS[tile_val],(rx,ry,TILE_SIZE,TILE_SIZE))

            # Draw items
            for (ix,iy,typ) in items:
                tile_x=int(ix//TILE_SIZE)
                tile_y=int(iy//TILE_SIZE)
                if not reveal_skill_active:
                    if current_level==5:
                        if fog_discovered and 0<=tile_y<GRID_HEIGHT and 0<=tile_x<GRID_WIDTH:
                            if not fog_discovered[tile_y][tile_x]:
                                continue
                    elif current_level==6:
                        if ephemeral_fog and 0<=tile_y<GRID_HEIGHT and 0<=tile_x<GRID_WIDTH:
                            if not ephemeral_fog[tile_y][tile_x]:
                                continue
                sx=offset_x+(ix -TILE_SIZE//2)
                sy=offset_y+(iy -TILE_SIZE//2)
                if typ=="point":
                    pygame.draw.circle(screen,POINT_COLOR,(sx+TILE_SIZE//2, sy+TILE_SIZE//2),TILE_SIZE//4)
                elif typ.startswith("key"):
                    c=KEY_COLORS[typ]
                    pygame.draw.circle(screen,c,(sx+TILE_SIZE//2, sy+TILE_SIZE//2),TILE_SIZE//4)
                elif typ=="finish_portal":
                    if points_collected >= points_in_level:
                        pygame.draw.rect(screen,FINISH_PORTAL_COLOR,
                                         (sx+TILE_SIZE//2-8, sy+TILE_SIZE//2-8,16,16))

            # Draw enemies
            for e in enemies:
                ex,ey = e['x'], e['y']
                tile_x=int(ex//TILE_SIZE)
                tile_y=int(ey//TILE_SIZE)
                if not reveal_skill_active:
                    if current_level==5:
                        if fog_discovered and 0<=tile_y<GRID_HEIGHT and 0<=tile_x<GRID_WIDTH:
                            if not fog_discovered[tile_y][tile_x]:
                                continue
                    elif current_level==6:
                        if ephemeral_fog and 0<=tile_y<GRID_HEIGHT and 0<=tile_x<GRID_WIDTH:
                            if not ephemeral_fog[tile_y][tile_x]:
                                continue

                sx=offset_x+(ex -TILE_SIZE//2)
                sy=offset_y+(ey -TILE_SIZE//2)
                pygame.draw.rect(screen,ENEMY_COLOR,(sx,sy,TILE_SIZE,TILE_SIZE))

            # Draw player
            px=offset_x+player_x
            py=offset_y+player_y
            draw_player_as_triangle(screen, px, py, direction_degs)

            # Menu button
            menu_button_rect=pygame.Rect(10,10,80,40)
            draw_button(screen, menu_button_rect, "Menu", font)

            # HUD
            p_txt = font.render(f"Points: {points_collected}/{points_in_level}", True, (255,255,255))
            screen.blit(p_txt,(10,60))
            k_txt = font.render(f"Keys: {keys_collected}/{keys_in_level}", True, (255,255,255))
            screen.blit(k_txt,(10,90))

            # Ghost skill HUD
            ghost_str = "Ready"
            if ghost_skill_cooldown>0:
                ghost_str = f"Cooldown: {int(ghost_skill_cooldown)}s"
            elif ghost_skill_uses_left<=0:
                ghost_str = "No uses left"
            elif ghost_skill_active:
                ghost_str = f"Active: {ghost_skill_timer:.1f}s"
            gs_txt = font.render(f"Ghost: {ghost_str}",True,(255,255,0))
            screen.blit(gs_txt,(10,120))

            # Reveal skill HUD
            reveal_str = "Ready"
            if reveal_skill_cooldown>0:
                reveal_str = f"Cooldown: {int(reveal_skill_cooldown)}s"
            elif reveal_skill_active:
                reveal_str = f"Reveal: {reveal_skill_timer:.1f}s"
            rv_txt = font.render(f"Reveal: {reveal_str}", True, (255,255,0))
            screen.blit(rv_txt,(10,150))

        elif game_state==STATE_INGAME_MENU:
            pygame.draw.rect(screen,(0,0,0),(0,0,screen.get_width(),screen.get_height()))
            t=font.render("In-Game Menu",True,(255,255,255))
            screen.blit(t,(screen.get_width()//2 - t.get_width()//2, 60))

            labels = ["Resume","Reset Level","Select Level","Options","Exit"]
            ingame_buttons = layout_menu_buttons(labels)
            for label, rct in ingame_buttons:
                draw_button(screen, rct, label, font)

        elif game_state==STATE_USER_SELECT:
            back_rect = pygame.Rect(20,20,100,40)
            draw_button(screen, back_rect,"Back", font)

            labels = ["New User"]
            user_buttons = layout_menu_buttons(labels)
            for label, rct in user_buttons:
                draw_button(screen, rct, label, font)

            t=font.render("Available Users:",True,(255,255,255))
            screen.blit(t,(screen.get_width()//2 - t.get_width()//2, 160))
            yy = 200
            for usr in data["profiles"]:
                r=pygame.Rect(0,0,200,40)
                r.centerx = screen.get_width()//2
                r.y = yy
                yy+=50
                draw_button(screen, r, usr, font)

        elif game_state==STATE_NEW_USER:
            r=font.render("Enter username:",True,(255,255,255))
            r_rect = r.get_rect(center=(screen.get_width()//2, 120))
            screen.blit(r, r_rect)

            new_user_input_rect=pygame.Rect(0,0,200,40)
            new_user_input_rect.center = (screen.get_width()//2, 180)
            pygame.draw.rect(screen,(255,255,255),new_user_input_rect,2)
            txt_surf=font.render(new_user_text,True,(255,255,255))
            screen.blit(txt_surf,(new_user_input_rect.x+5,new_user_input_rect.y+5))

            create_rect = pygame.Rect(0,0,150,40)
            create_rect.center = (screen.get_width()//2, 250)
            draw_button(screen, create_rect, "Create", font)

            if user_message:
                msg_s=font.render(user_message,True,(255,0,0))
                msg_rect = msg_s.get_rect(center=(screen.get_width()//2, 300))
                screen.blit(msg_s, msg_rect)

        elif game_state==STATE_END_LEVEL:
            screen.blit(font.render("Level End Scoreboard",True,(255,255,255)),
                        (screen.get_width()//2 - 100,50))
            if profile:
                ls=profile["level_scores"]
                y=100
                total=0
                for lvl in range(1,MAX_LEVEL+1):
                    sc=ls[lvl]
                    line=f"Level {lvl} => {sc} points"
                    screen.blit(font.render(line,True,(255,255,255)),
                                (screen.get_width()//2 - 100,y))
                    y+=30
                    total+=sc
                screen.blit(font.render(f"Total = {total}",True,(255,255,0)),
                            (screen.get_width()//2 - 50,y))

            labels = ["Next Level","Menu"]
            endlevel_buttons = layout_menu_buttons(labels)
            for label, rct in endlevel_buttons:
                draw_button(screen, rct, label, font)

        pygame.display.flip()
        clock.tick(60)

    save_profiles(data)
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
