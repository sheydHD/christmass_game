# rendering.py

import pygame
from config import (
    GRID_WIDTH, GRID_HEIGHT, TILE_SIZE,
    WALL_COLOR, DOOR_COLORS, KEY_COLORS,
    POINT_COLOR, FINISH_PORTAL_COLOR, ENEMY_COLOR
)
from utils import draw_player_as_triangle

def draw_maze(screen, maze, offset_x, offset_y, fog_check_fn=None):
    for yy in range(GRID_HEIGHT):
        for xx in range(GRID_WIDTH):
            rx=offset_x+xx*TILE_SIZE
            ry=offset_y+yy*TILE_SIZE
            visible=True
            if fog_check_fn and not fog_check_fn(xx, yy):
                visible=False
            if not visible:
                pygame.draw.rect(screen,(0,0,0),(rx,ry,TILE_SIZE,TILE_SIZE))
                continue

            tv=maze[yy][xx]
            if tv==1:
                pygame.draw.rect(screen,WALL_COLOR,(rx,ry,TILE_SIZE,TILE_SIZE))
            elif tv in (2,3,4):
                pygame.draw.rect(screen, DOOR_COLORS[tv],(rx,ry,TILE_SIZE,TILE_SIZE))

def draw_items(screen, items, offset_x, offset_y,
               fog_check_fn=None,
               points_in_level=0, points_collected=0,
               reveal_active=False):
    for (ix, iy, typ) in items:
        tx=int(ix//TILE_SIZE)
        ty=int(iy//TILE_SIZE)

        if not reveal_active and fog_check_fn:
            if not fog_check_fn(tx, ty):
                continue

        sx=offset_x+(ix - TILE_SIZE//2)
        sy=offset_y+(iy - TILE_SIZE//2)
        if typ=="point":
            pygame.draw.circle(screen, POINT_COLOR,
                               (sx+TILE_SIZE//2, sy+TILE_SIZE//2),
                               TILE_SIZE//4)
        elif typ.startswith("key"):
            c=KEY_COLORS[typ]
            pygame.draw.circle(screen, c,
                               (sx+TILE_SIZE//2, sy+TILE_SIZE//2),
                               TILE_SIZE//4)
        elif typ=="finish_portal":
            if points_collected >= points_in_level:
                pygame.draw.rect(screen, FINISH_PORTAL_COLOR,
                                 (sx+TILE_SIZE//2-8, sy+TILE_SIZE//2-8,16,16))

def draw_enemies(screen, enemies, offset_x, offset_y,
                 fog_check_fn=None, reveal_active=False):
    for e in enemies:
        ex, ey = e['x'], e['y']
        tx=int(ex//TILE_SIZE)
        ty=int(ey//TILE_SIZE)
        if not reveal_active and fog_check_fn:
            if not fog_check_fn(tx,ty):
                continue
        sx=offset_x+(ex -TILE_SIZE//2)
        sy=offset_y+(ey -TILE_SIZE//2)
        pygame.draw.rect(screen, ENEMY_COLOR, (sx, sy, TILE_SIZE, TILE_SIZE))

def draw_player(screen, px, py, direction_degs,
                offset_x, offset_y):
    sx=offset_x+px
    sy=offset_y+py
    draw_player_as_triangle(screen, sx, sy, direction_degs)
