# items.py

import random
from config import GRID_WIDTH, GRID_HEIGHT, TILE_SIZE, POINT_COUNT

def spawn_items(maze, count, item_type):
    """Spawn 'count' items of given type in empty tiles."""
    items=[]
    h=len(maze)
    w=len(maze[0])
    tries=0
    while len(items)<count and tries<5000:
        tries+=1
        tx=random.randint(1,w-2)
        ty=random.randint(1,h-2)
        if maze[ty][tx]==0:
            px=tx*TILE_SIZE + TILE_SIZE//2
            py=ty*TILE_SIZE + TILE_SIZE//2
            items.append([px,py,item_type])
    return items

def spawn_keys(maze):
    all_keys=[]
    for kt in ["key0","key1","key2"]:
        one=spawn_items(maze,1,kt)
        all_keys.extend(one)
    return all_keys

def spawn_finish_portal(maze):
    tries=0
    while tries<5000:
        tries+=1
        import random
        tx=random.randint(1,GRID_WIDTH-2)
        ty=random.randint(1,GRID_HEIGHT-2)
        if maze[ty][tx]==0:
            px=tx*TILE_SIZE+TILE_SIZE//2
            py=ty*TILE_SIZE+TILE_SIZE//2
            return [px,py,"finish_portal"]
    return None
