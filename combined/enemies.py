# enemies.py

import random
from config import GRID_WIDTH, GRID_HEIGHT, TILE_SIZE, PLAYER_SPEED

def spawn_enemies_for_level(maze, level):
    """Spawn 'level' enemies if level >=3."""
    if level < 3:
        return []
    count = level
    enemies = []
    h=len(maze)
    w=len(maze[0])
    tries=0
    while len(enemies)<count and tries<3000:
        tries+=1
        tx=random.randint(1,w-2)
        ty=random.randint(1,h-2)
        if maze[ty][tx]==0:
            ex=tx*TILE_SIZE+TILE_SIZE//2
            ey=ty*TILE_SIZE+TILE_SIZE//2
            dx=random.choice([-1,0,1])
            dy=random.choice([-1,0,1])
            if dx==0 and dy==0:
                dx=1
            enemies.append({
                'x':ex,'y':ey,
                'dx':dx,'dy':dy,
                'dir_change_cooldown':random.uniform(1.0,3.0)
            })
    return enemies

def move_enemies(enemies, dt):
    sp=PLAYER_SPEED*TILE_SIZE*0.5
    for e in enemies:
        e['dir_change_cooldown']-=dt
        if e['dir_change_cooldown']<=0:
            e['dx']=random.choice([-1,0,1])
            e['dy']=random.choice([-1,0,1])
            if e['dx']==0 and e['dy']==0:
                e['dx']=1
            e['dir_change_cooldown']=random.uniform(1.0,3.0)

        e['x']+=e['dx']*sp*dt
        e['y']+=e['dy']*sp*dt

        # keep them in-bounds
        if e['x']<0:
            e['x']=0
            e['dx']=random.choice([-1,0,1])
        elif e['x']>GRID_WIDTH*TILE_SIZE:
            e['x']=GRID_WIDTH*TILE_SIZE
            e['dx']=random.choice([-1,0,1])
        if e['y']<0:
            e['y']=0
            e['dy']=random.choice([-1,0,1])
        elif e['y']>GRID_HEIGHT*TILE_SIZE:
            e['y']=GRID_HEIGHT*TILE_SIZE
            e['dy']=random.choice([-1,0,1])

def check_enemy_collision(px, py, enemies):
    for e in enemies:
        ex, ey = e['x'], e['y']
        dist_sq = (px - ex)**2 + (py - ey)**2
        if dist_sq < (TILE_SIZE//2)**2:
            return True
    return False
