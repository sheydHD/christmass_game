# utils.py

import pygame
import math

from config import TILE_SIZE, BUTTON_BG, BUTTON_TEXT

def draw_player_as_triangle(screen, x, y, direction_degs):
    size=int(TILE_SIZE*0.7)
    half=size//2
    local_points=[
        (half,0),
        (-half,int(0.6*half)),
        (-half,-int(0.6*half)),
    ]
    rad=math.radians(direction_degs)
    cos_a, sin_a=math.cos(rad), math.sin(rad)
    rotated=[]
    for lx,ly in local_points:
        rx=lx*cos_a - ly*sin_a
        ry=lx*sin_a + ly*cos_a
        rotated.append((x+rx,y+ry))
    pygame.draw.polygon(screen,(255,0,0),rotated)

def draw_button(screen, rect, text, font,
                bg_color=BUTTON_BG, text_color=BUTTON_TEXT):
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
