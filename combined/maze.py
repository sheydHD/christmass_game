# maze.py

import random
from config import (
    GRID_WIDTH, GRID_HEIGHT,
    ROOM_COUNT, MAX_ROOM_SIZE, DOOR_COUNT
)

def generate_maze(width, height):
    """Generate a random maze using DFS backtracking."""
    maze=[[1 for _ in range(width)] for _ in range(height)]
    stack=[(1,1)]
    maze[1][1]=0
    directions=[(-1,0),(1,0),(0,-1),(0,1)]
    while stack:
        x,y=stack[-1]
        neighbors=[]
        for dx,dy in directions:
            nx,ny=x+dx*2,y+dy*2
            if 0<nx<width-1 and 0<ny<height-1:
                if maze[ny][nx]==1:
                    neighbors.append((nx,ny,dx,dy))
        if neighbors:
            nx,ny,dx,dy=random.choice(neighbors)
            maze[ny][nx]=0
            maze[y+dy][x+dx]=0
            stack.append((nx,ny))
        else:
            stack.pop()

    # border walls
    for i in range(width):
        maze[0][i]=1
        maze[height-1][i]=1
    for j in range(height):
        maze[j][0]=1
        maze[j][width-1]=1
    return maze

def carve_rooms(maze, room_count=ROOM_COUNT, max_room_size=MAX_ROOM_SIZE):
    h=len(maze)
    w=len(maze[0])
    for _ in range(room_count):
        rw=random.randint(3, max_room_size)
        rh=random.randint(3, max_room_size)
        x=random.randint(2, w-rw-2)
        y=random.randint(2, h-rh-2)
        for ry in range(y,y+rh):
            for rx in range(x,x+rw):
                maze[ry][rx]=0

def place_doors(maze, door_count=DOOR_COUNT):
    door_vals=[2,3,4]
    random.shuffle(door_vals)
    h=len(maze)
    w=len(maze[0])
    placed=0
    tries=0
    while placed<door_count and tries<1000:
        tries+=1
        xx=random.randint(2,w-3)
        yy=random.randint(2,h-3)
        if maze[yy][xx]==0:
            maze[yy][xx]=door_vals[placed]
            placed+=1
