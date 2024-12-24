# game_logic.py

import math
from collections import defaultdict, deque
from config import (
    GRID_WIDTH, GRID_HEIGHT, TILE_SIZE, 
    POINT_COUNT, MAX_LEVEL,
    LEVEL_BG_COLORS
)
from maze import generate_maze, carve_rooms, place_doors
from items import spawn_items, spawn_keys, spawn_finish_portal
from enemies import spawn_enemies_for_level

# -------------------------------------------------------------------------
# BFS VALIDATION
# -------------------------------------------------------------------------
def can_pass_tile(tile_val, key_inv):
    if tile_val == 1:
        return False
    elif tile_val in (2,3,4):
        needed_key = f"key{tile_val-2}"
        return (key_inv[needed_key] > 0)
    else:
        return True

def is_level_valid(maze, items):
    item_coords=[]
    portal_coord=None
    for (px,py,typ) in items:
        tx=px//TILE_SIZE
        ty=py//TILE_SIZE
        item_coords.append((tx,ty,typ))
        if typ=="finish_portal":
            portal_coord=(tx,ty)

    visited=set()
    queue=deque()
    start=(1,1,0,0,0)
    visited.add(start)
    queue.append(start)
    found_items=set()
    directions=[(-1,0),(1,0),(0,-1),(0,1)]

    while queue:
        cx,cy,k0,k1,k2=queue.popleft()
        for (ix,iy,typ) in item_coords:
            if (ix,iy)==(cx,cy) and (ix,iy) not in found_items:
                found_items.add((ix,iy))
                nk0,nk1,nk2=k0,k1,k2
                if typ.startswith("key"):
                    if typ=="key0": nk0=1
                    if typ=="key1": nk1=1
                    if typ=="key2": nk2=1
                new_st=(cx,cy,nk0,nk1,nk2)
                if new_st not in visited:
                    visited.add(new_st)
                    queue.append(new_st)

        keys_dict={"key0":k0,"key1":k1,"key2":k2}
        for dx,dy in directions:
            nx,ny=cx+dx,cy+dy
            if 0<=nx<GRID_WIDTH and 0<=ny<GRID_HEIGHT:
                tile_val=maze[ny][nx]
                # check pass
                if tile_val==1:
                    passable=False
                elif tile_val in (2,3,4):
                    needed_key=f"key{tile_val-2}"
                    passable = (keys_dict[needed_key]>0)
                else:
                    passable=True

                if passable:
                    st=(nx,ny,k0,k1,k2)
                    if st not in visited:
                        visited.add(st)
                        queue.append(st)

    # check if all items (point/key) are found
    for (ix,iy,typ) in item_coords:
        if typ in ("point","key0","key1","key2") and (ix,iy) not in found_items:
            return False

    # check if finish portal is reachable
    if portal_coord:
        px,py=portal_coord
        if not any((px,py,a,b,c) in visited for a in [0,1] for b in [0,1] for c in [0,1]):
            return False

    # ensure all floor tiles visited
    for yy in range(GRID_HEIGHT):
        for xx in range(GRID_WIDTH):
            if maze[yy][xx]==0:
                if not any((xx,yy,a,b,c) in visited for a in [0,1] for b in [0,1] for c in [0,1]):
                    return False
    return True

# -------------------------------------------------------------------------
def create_level_until_valid(level):
    """Generate a random layout that BFS says is solvable."""
    while True:
        maze=generate_maze(GRID_WIDTH, GRID_HEIGHT)
        carve_rooms(maze)
        if maze[1][1]==1:
            continue
        items=[]
        if level>=2:
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
# Fog of War
# -------------------------------------------------------------------------
def update_fog_of_war_permanent(discovered,px,py,radius=5):
    tile_x=int(px//TILE_SIZE)
    tile_y=int(py//TILE_SIZE)
    for yy in range(tile_y-radius, tile_y+radius+1):
        for xx in range(tile_x-radius, tile_x+radius+1):
            if 0<=xx<GRID_WIDTH and 0<=yy<GRID_HEIGHT:
                dist_sq=(xx-tile_x)**2+(yy-tile_y)**2
                if dist_sq<=radius**2:
                    discovered[yy][xx]=True

def update_fog_of_war_ephemeral(px,py,radius=5):
    tile_x=int(px//TILE_SIZE)
    tile_y=int(py//TILE_SIZE)
    ephemeral=[[False for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
    for yy in range(tile_y-radius, tile_y+radius+1):
        for xx in range(tile_x-radius, tile_x+radius+1):
            if 0<=xx<GRID_WIDTH and 0<=yy<GRID_HEIGHT:
                dist_sq=(xx-tile_x)**2+(yy-tile_y)**2
                if dist_sq<=radius**2:
                    ephemeral[yy][xx]=True
    return ephemeral

# -------------------------------------------------------------------------
def setup_level(level):
    maze, items = create_level_until_valid(level)
    enemies = spawn_enemies_for_level(maze, level)
    bg_color = LEVEL_BG_COLORS.get(level,(100,100,100))
    fog_discovered=None
    if level==5 or level==6:
        fog_discovered=[[False for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

    points_in_level = sum(1 for i in items if i[2]=="point")
    keys_in_level   = sum(1 for i in items if i[2].startswith("key"))
    return maze, items, bg_color, enemies, fog_discovered, points_in_level, keys_in_level

# -------------------------------------------------------------------------
# Movement logic with Ghost skill usage (like original)
# -------------------------------------------------------------------------
def tile_passable_with_ghost(maze, tx, ty, key_inventory,
                             ghost_active, ghost_skill_wall_passed):
    if not (0<=tx<GRID_WIDTH and 0<=ty<GRID_HEIGHT):
        return False
    tv = maze[ty][tx]
    if tv==0:
        return True
    elif tv in (2,3,4):
        needed_key=f"key{tv-2}"
        return (key_inventory[needed_key]>0)
    elif tv==1:
        if ghost_active and not ghost_skill_wall_passed:
            return True
        return False
    return True

def move_player_with_diagonal(player_x, player_y, vel_x, vel_y,
                              maze, key_inventory,
                              ghost_active, ghost_skill_wall_passed):
    old_px = player_x
    old_py = player_y

    # X movement
    temp_x = player_x + vel_x
    temp_y = player_y
    tx=int(temp_x//TILE_SIZE)
    ty=int(temp_y//TILE_SIZE)
    if tile_passable_with_ghost(maze, tx, ty, key_inventory,
                                ghost_active, ghost_skill_wall_passed):
        # If it's a wall, consume pass
        if maze[ty][tx]==1 and ghost_active and not ghost_skill_wall_passed:
            ghost_skill_wall_passed=True
        player_x = temp_x

    # Y movement
    temp_x = player_x
    temp_y = player_y + vel_y
    tx=int(temp_x//TILE_SIZE)
    ty=int(temp_y//TILE_SIZE)
    if tile_passable_with_ghost(maze, tx, ty, key_inventory,
                                ghost_active, ghost_skill_wall_passed):
        if maze[ty][tx]==1 and ghost_active and not ghost_skill_wall_passed:
            ghost_skill_wall_passed=True
        player_y = temp_y

    return player_x, player_y, ghost_skill_wall_passed
