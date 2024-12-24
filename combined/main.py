# main.py

import pygame
import sys
import math
from collections import defaultdict

from config import (
    DISPLAY_MODES,
    STATE_MENU, STATE_GAME, STATE_OPTIONS, STATE_GAME_RULES,
    STATE_LEVEL_SELECT, STATE_INGAME_MENU, STATE_END_LEVEL,
    STATE_USER_SELECT, STATE_NEW_USER, PLAYER_SPEED,
    POINT_COUNT, MAX_LEVEL,
    BUTTON_BG, BUTTON_TEXT, TEXT_COLOR
)
from profiles import load_profiles, save_profiles, get_or_create_profile
from game_logic import (
    setup_level, move_player_with_diagonal,
    update_fog_of_war_permanent, update_fog_of_war_ephemeral
)
from enemies import move_enemies, check_enemy_collision
from rendering import draw_maze, draw_items, draw_enemies, draw_player
from utils import draw_button


def apply_display_mode(mode):
    """Apply display mode: 'maximized' or 'fullscreen'."""
    if mode == "fullscreen":
        return pygame.display.set_mode((0,0), pygame.FULLSCREEN)
    else:
        # default to 'maximized'
        info=pygame.display.Info()
        return pygame.display.set_mode((info.current_w, info.current_h), pygame.RESIZABLE)

def main():
    pygame.init()
    data = load_profiles()
    current_user = None
    profile = None

    # pick first user if exist:
    if data["profiles"]:
        first_user = list(data["profiles"].keys())[0]
        profile = get_or_create_profile(data, first_user)
        current_user = first_user
        screen = apply_display_mode(profile.get("display_mode", "maximized"))
    else:
        # if no profiles, default to 'maximized'
        screen = apply_display_mode("maximized")

    pygame.display.set_caption("Christmas Game")

    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 32)

    game_state=STATE_MENU

    def switch_user(username):
        nonlocal current_user, profile, screen
        current_user=username
        profile = get_or_create_profile(data, username)
        new_mode = profile.get("display_mode", "maximized")
        screen = apply_display_mode(new_mode)

    # Profile access helpers
    def get_highest_unlocked_level():
        return profile["highest_unlocked_level"]
    def set_highest_unlocked_level(l):
        profile["highest_unlocked_level"] = l
    def get_level_score(lvl):
        return profile["level_scores"][lvl]
    def add_level_score(lvl, amount):
        profile["level_scores"][lvl]+=amount

    # level data
    current_level=1
    maze=[]
    items=[]
    background_color=(50,50,50)
    enemies=[]
    fog_discovered=None

    points_in_level=0
    keys_in_level=0
    points_collected=0
    keys_collected=0
    key_inventory=defaultdict(int)

    # ghost skill
    ghost_skill_active=False
    ghost_skill_timer=0.0
    ghost_skill_cooldown=0.0
    ghost_skill_uses_left=3
    ghost_skill_wall_passed=False

    # reveal skill
    reveal_skill_active=False
    reveal_skill_timer=0.0
    reveal_skill_cooldown=0.0

    # track player
    player_x=player_y=0
    direction_degs=0.0

    def reset_level(lvl):
        nonlocal maze,items,background_color,enemies,fog_discovered
        nonlocal player_x,player_y,direction_degs,key_inventory
        nonlocal points_in_level,keys_in_level,points_collected,keys_collected
        nonlocal ghost_skill_active, ghost_skill_timer, ghost_skill_cooldown
        nonlocal ghost_skill_uses_left, ghost_skill_wall_passed
        nonlocal reveal_skill_active, reveal_skill_timer, reveal_skill_cooldown

        # reset skill
        ghost_skill_active=False
        ghost_skill_timer=0.0
        ghost_skill_cooldown=0.0
        ghost_skill_uses_left=3
        ghost_skill_wall_passed=False

        reveal_skill_active=False
        reveal_skill_timer=0.0
        reveal_skill_cooldown=0.0

        key_inventory=defaultdict(int)
        points_collected=0
        keys_collected=0
        direction_degs=0.0

        m, its, bg, en, fd, p_cnt, k_cnt = setup_level(lvl)
        maze=m
        items=its
        background_color=bg
        enemies=en
        fog_discovered=fd
        points_in_level=p_cnt
        keys_in_level=k_cnt

        player_x=1.5*32
        player_y=1.5*32

    def go_to_level(lvl):
        nonlocal current_level, game_state
        current_level=lvl
        reset_level(lvl)
        game_state=STATE_GAME

    new_user_text=""
    user_message=""

    # layout helper
    BUTTON_WIDTH=220
    BUTTON_HEIGHT=50
    BUTTON_SPACING=10
    def layout_menu_buttons(labels):
        sw=screen.get_width()
        sh=screen.get_height()
        total_height=len(labels)*(BUTTON_HEIGHT+BUTTON_SPACING)
        start_y=(sh-total_height)//2
        result=[]
        for i,txt in enumerate(labels):
            rect=pygame.Rect(0,0,BUTTON_WIDTH,BUTTON_HEIGHT)
            rect.centerx=sw//2
            rect.y=start_y + i*(BUTTON_HEIGHT+BUTTON_SPACING)
            result.append((txt,rect))
        return result

    running=True
    now_time=pygame.time.get_ticks()/1000.0
    prev_time=now_time

    while running:
        now_time=pygame.time.get_ticks()/1000.0
        dt=now_time - prev_time
        prev_time=now_time

        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                running=False
            elif event.type==pygame.KEYDOWN:
                if game_state==STATE_NEW_USER:
                    if event.key==pygame.K_BACKSPACE and len(new_user_text)>0:
                        new_user_text=new_user_text[:-1]
                    elif event.key==pygame.K_RETURN:
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
                            new_user_text+=event.unicode

                elif game_state==STATE_GAME:
                    # ghost skill
                    if event.key==pygame.K_SPACE:
                        if (not ghost_skill_active
                            and ghost_skill_cooldown<=0
                            and ghost_skill_uses_left>0):
                            # optionally check border
                            ghost_skill_active=True
                            ghost_skill_timer=2.0
                            ghost_skill_cooldown=15.0
                            ghost_skill_uses_left-=1
                            ghost_skill_wall_passed=False

                    # reveal skill
                    elif event.key==pygame.K_q:
                        if (not reveal_skill_active
                            and reveal_skill_cooldown<=0):
                            reveal_skill_active=True
                            reveal_skill_timer=5.0
                            reveal_skill_cooldown=20.0

            elif event.type==pygame.MOUSEBUTTONDOWN:
                if event.button==1:
                    mx,my=event.pos
                    if game_state==STATE_MENU:
                        # show menu
                        if profile:
                            menu_labels=["Start Game","Select Level","Options","Game Rules","Exit","Switch User"]
                        else:
                            menu_labels=["Switch User"]

                        menu_buttons=layout_menu_buttons(menu_labels)
                        for label,rect in menu_buttons:
                            if rect.collidepoint(mx,my):
                                if label=="Start Game":
                                    go_to_level(profile["highest_unlocked_level"])
                                elif label=="Select Level":
                                    game_state=STATE_LEVEL_SELECT
                                elif label=="Options":
                                    game_state=STATE_OPTIONS
                                elif label=="Game Rules":
                                    game_state=STATE_GAME_RULES
                                elif label=="Exit":
                                    running=False
                                elif label=="Switch User":
                                    game_state=STATE_USER_SELECT
                                break

                    elif game_state==STATE_LEVEL_SELECT:
                        back_rect=pygame.Rect(20,20,100,40)
                        if back_rect.collidepoint(mx,my):
                            game_state=STATE_MENU
                        else:
                            labels=[f"Level {l}" for l in range(1,MAX_LEVEL+1)]
                            lvl_buttons=layout_menu_buttons(labels)
                            hul=profile["highest_unlocked_level"] if profile else 1
                            for i,(lbl,rct) in enumerate(lvl_buttons, start=1):
                                if rct.collidepoint(mx,my):
                                    if i<=hul:
                                        go_to_level(i)
                                    break

                    elif game_state==STATE_OPTIONS:
                        back_rect=pygame.Rect(20,20,100,40)
                        if back_rect.collidepoint(mx,my):
                            game_state=STATE_MENU
                        else:
                            labels=["Display Mode","Reset Stats","Full Screen","Back To Menu"]
                            opts_buttons=layout_menu_buttons(labels)
                            for label,rct in opts_buttons:
                                if rct.collidepoint(mx,my):
                                    if label=="Display Mode":
                                        current_mode=profile.get("display_mode","maximized")
                                        modes=DISPLAY_MODES
                                        idx=modes.index(current_mode)
                                        idx=(idx+1)%len(modes)
                                        new_mode=modes[idx]
                                        profile["display_mode"]=new_mode
                                        screen=apply_display_mode(new_mode)
                                        save_profiles(data)
                                    elif label=="Reset Stats":
                                        profile["score"]=0
                                        profile["highest_unlocked_level"]=1
                                        profile["level_scores"]=[0]*(MAX_LEVEL+1)
                                        save_profiles(data)
                                    elif label=="Full Screen":
                                        profile["display_mode"]="fullscreen"
                                        screen=apply_display_mode("fullscreen")
                                        save_profiles(data)
                                    elif label=="Back To Menu":
                                        game_state=STATE_MENU
                                    break

                    elif game_state==STATE_GAME_RULES:
                        back_rect=pygame.Rect(20,20,100,40)
                        if back_rect.collidepoint(mx,my):
                            game_state=STATE_MENU

                    elif game_state==STATE_GAME:
                        menu_button_rect=pygame.Rect(10,10,80,40)
                        if menu_button_rect.collidepoint(mx,my):
                            game_state=STATE_INGAME_MENU

                    elif game_state==STATE_INGAME_MENU:
                        labels=["Resume","Reset Level","Select Level","Options","Exit"]
                        ingame_buttons=layout_menu_buttons(labels)
                        for label,rct in ingame_buttons:
                            if rct.collidepoint(mx,my):
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

                    elif game_state==STATE_USER_SELECT:
                        back_rect=pygame.Rect(20,20,100,40)
                        if back_rect.collidepoint(mx,my):
                            game_state=STATE_MENU
                        else:
                            labels=["New User"]
                            user_buttons=layout_menu_buttons(labels)
                            clicked_new_user=False
                            for (lbl,rct) in user_buttons:
                                if rct.collidepoint(mx,my):
                                    if lbl=="New User":
                                        game_state=STATE_NEW_USER
                                        clicked_new_user=True
                                    break
                            if not clicked_new_user:
                                yy=200
                                for usr in data["profiles"]:
                                    r=pygame.Rect(0,0,200,40)
                                    r.centerx=screen.get_width()//2
                                    r.y=yy
                                    yy+=50
                                    if r.collidepoint(mx,my):
                                        switch_user(usr)
                                        save_profiles(data)
                                        game_state=STATE_MENU
                                        break

                    elif game_state==STATE_NEW_USER:
                        create_rect=pygame.Rect(0,0,150,40)
                        create_rect.center=(screen.get_width()//2,250)
                        if create_rect.collidepoint(mx,my):
                            if new_user_text.strip():
                                if new_user_text in data["profiles"]:
                                    user_message="Username already exists!"
                                else:
                                    switch_user(new_user_text.strip())
                                    user_message="User created!"
                                    game_state=STATE_MENU
                                    save_profiles(data)

                    elif game_state==STATE_END_LEVEL:
                        labels=["Next Level","Menu"]
                        endlevel_buttons=layout_menu_buttons(labels)
                        for label,rct in endlevel_buttons:
                            if rct.collidepoint(mx,my):
                                if label=="Next Level":
                                    if current_level<MAX_LEVEL:
                                        go_to_level(current_level+1)
                                    else:
                                        game_state=STATE_MENU
                                elif label=="Menu":
                                    game_state=STATE_MENU
                                break

        # UPDATE
        if game_state==STATE_GAME and profile:
            # update skill timers
            if ghost_skill_cooldown>0:
                ghost_skill_cooldown-=dt
                if ghost_skill_cooldown<0:
                    ghost_skill_cooldown=0
            if ghost_skill_active:
                ghost_skill_timer-=dt
                if ghost_skill_timer<=0:
                    ghost_skill_active=False
                    # if still in wall, push out
                    tile_x=int(player_x//32)
                    tile_y=int(player_y//32)
                    if maze[tile_y][tile_x]==1:
                        # push out
                        player_x=1.5*32
                        player_y=1.5*32
                    ghost_skill_wall_passed=False

            if reveal_skill_cooldown>0:
                reveal_skill_cooldown-=dt
                if reveal_skill_cooldown<0:
                    reveal_skill_cooldown=0
            if reveal_skill_active:
                reveal_skill_timer-=dt
                if reveal_skill_timer<=0:
                    reveal_skill_active=False

            # movement
            keys=pygame.key.get_pressed()
            vel_x=vel_y=0
            if keys[pygame.K_w]:
                vel_y=-PLAYER_SPEED
            if keys[pygame.K_s]:
                vel_y=PLAYER_SPEED
            if keys[pygame.K_a]:
                vel_x=-PLAYER_SPEED
            if keys[pygame.K_d]:
                vel_x=PLAYER_SPEED

            if abs(vel_x)>0.01 or abs(vel_y)>0.01:
                direction_degs=math.degrees(math.atan2(vel_y,vel_x))

            player_x, player_y, ghost_skill_wall_passed = \
                move_player_with_diagonal(
                    player_x, player_y,
                    vel_x, vel_y,
                    maze, key_inventory,
                    ghost_skill_active, ghost_skill_wall_passed
                )

            # enemies
            move_enemies(enemies, dt)
            if check_enemy_collision(player_x,player_y,enemies):
                reset_level(current_level)
                continue

            # item pickup
            for it in items[:]:
                ix,iy,typ=it
                dist_sq=(player_x-ix)**2 + (player_y-iy)**2
                if dist_sq<(32//2)**2:
                    if typ=="point":
                        items.remove(it)
                        points_collected+=1
                    elif typ.startswith("key"):
                        items.remove(it)
                        keys_collected+=1
                        key_inventory[typ]+=1
                    elif typ=="finish_portal":
                        if points_collected>=points_in_level:
                            items.remove(it)
                            game_state=STATE_END_LEVEL

            # fog
            if current_level==5 and fog_discovered:
                # permanent
                from game_logic import update_fog_of_war_permanent
                update_fog_of_war_permanent(fog_discovered, player_x, player_y, 5)
            elif current_level==6:
                from game_logic import update_fog_of_war_ephemeral
                ephemeral_fog=update_fog_of_war_ephemeral(player_x, player_y, 5)
                # store ephemeral_fog in a local var
                # then in rendering we skip tile if ephemeral_fog[y][x]==False
                pass

        # RENDER
        screen.fill((20,20,20))
        if game_state==STATE_MENU:
            if profile:
                menu_labels=["Start Game","Select Level","Options","Game Rules","Exit","Switch User"]
            else:
                menu_labels=["Switch User"]

            title_txt=font.render("MAIN MENU", True, (255,255,255))
            title_rect=title_txt.get_rect(center=(screen.get_width()//2,80))
            screen.blit(title_txt, title_rect)

            user_str=f"Current user: {current_user if current_user else 'None'}"
            user_txt=font.render(user_str, True, (255,255,255))
            user_rect=user_txt.get_rect(center=(screen.get_width()//2,130))
            screen.blit(user_txt, user_rect)

            menu_buttons=layout_menu_buttons(menu_labels)
            for label, rect in menu_buttons:
                draw_button(screen, rect, label, font)

        elif game_state==STATE_LEVEL_SELECT:
            back_rect=pygame.Rect(20,20,100,40)
            draw_button(screen, back_rect,"Back", font)
            t=font.render("Select Level:", True, (255,255,255))
            screen.blit(t,(50,80))

            labels=[f"Level {l}" for l in range(1,MAX_LEVEL+1)]
            lvl_buttons=layout_menu_buttons(labels)
            hul=profile["highest_unlocked_level"] if profile else 1
            for i,(lbl,rct) in enumerate(lvl_buttons, start=1):
                if i<=hul:
                    draw_button(screen, rct, lbl, font)
                else:
                    pygame.draw.rect(screen, (150,150,150), rct)
                    s=font.render(lbl,True,(80,80,80))
                    s_rect=s.get_rect(center=rct.center)
                    screen.blit(s, s_rect)

        elif game_state==STATE_OPTIONS:
            back_rect=pygame.Rect(20,20,100,40)
            draw_button(screen, back_rect,"Back",font)

            labels=["Display Mode","Reset Stats","Full Screen","Back To Menu"]
            opts_buttons=layout_menu_buttons(labels)

            mode_txt = profile.get("display_mode","maximized") if profile else "maximized"
            m_surf=font.render(f"Current Mode: {mode_txt}",True,(255,255,255))
            screen.blit(m_surf,(screen.get_width()//2 - m_surf.get_width()//2,150))

            for label,rct in opts_buttons:
                draw_button(screen, rct, label, font)

        elif game_state==STATE_GAME_RULES:
            back_rect=pygame.Rect(20,20,100,40)
            draw_button(screen, back_rect,"Back", font)

            lines=[
                "GAME RULES:",
                "- Move with W/A/S/D.",
                "- Collect ALL points before the finish portal is usable.",
                "- Keys open colored doors.",
                "- Fog: L5 = permanent, L6 = ephemeral.",
                "- SPACE: pass 1 wall (2s, 15s cooldown, 3 uses).",
                "- Q: reveal items for 5s (20s cooldown).",
                "- Press 'Menu' in top-left while in game."
            ]
            yy=80
            for l in lines:
                r=font.render(l,True,(255,255,255))
                screen.blit(r,(50,yy))
                yy+=40

        elif game_state==STATE_GAME:
            offset_x=(screen.get_width()-32*48)//2
            offset_y=(screen.get_height()-32*27)//2

            ephemeral_fog=None
            if current_level==6:
                # ephemeral fog might be updated in the update step
                pass

            def fog_check_fn_tile(x,y):
                # If reveal is active, ignore fog
                if reveal_skill_active:
                    return True

                if current_level==5 and fog_discovered:
                    return fog_discovered[y][x]
                elif current_level==6 and ephemeral_fog:
                    return ephemeral_fog[y][x]
                else:
                    return True

            # draw maze
            draw_maze(screen, maze, offset_x, offset_y,
                      fog_check_fn=fog_check_fn_tile)

            # draw items
            draw_items(screen, items, offset_x, offset_y,
                       fog_check_fn=fog_check_fn_tile,
                       points_in_level=points_in_level,
                       points_collected=points_collected,
                       reveal_active=reveal_skill_active)

            # draw enemies
            draw_enemies(screen, enemies, offset_x, offset_y,
                         fog_check_fn=fog_check_fn_tile,
                         reveal_active=reveal_skill_active)

            # draw player
            draw_player(screen, player_x, player_y, direction_degs,
                        offset_x, offset_y)

            menu_button_rect=pygame.Rect(10,10,80,40)
            draw_button(screen, menu_button_rect,"Menu", font)

            p_txt=font.render(f"Points: {points_collected}/{points_in_level}", True, (255,255,255))
            screen.blit(p_txt,(10,60))
            k_txt=font.render(f"Keys: {keys_collected}/{keys_in_level}", True, (255,255,255))
            screen.blit(k_txt,(10,90))

            # ghost skill hud
            if ghost_skill_cooldown>0:
                ghost_str=f"Cooldown: {int(ghost_skill_cooldown)}s"
            elif ghost_skill_uses_left<=0:
                ghost_str="No uses left"
            elif ghost_skill_active:
                ghost_str=f"Ghost: {ghost_skill_timer:.1f}s"
            else:
                ghost_str="Ready"

            gs_txt=font.render(f"Wall-Pass: {ghost_str}", True, (255,255,0))
            screen.blit(gs_txt,(10,120))

            # reveal skill hud
            if reveal_skill_cooldown>0:
                reveal_str=f"Cooldown: {int(reveal_skill_cooldown)}s"
            elif reveal_skill_active:
                reveal_str=f"Reveal: {reveal_skill_timer:.1f}s"
            else:
                reveal_str="Ready"
            rv_txt=font.render(f"Reveal: {reveal_str}", True, (255,255,0))
            screen.blit(rv_txt,(10,150))

        elif game_state==STATE_INGAME_MENU:
            pygame.draw.rect(screen,(0,0,0),(0,0,screen.get_width(),screen.get_height()))
            t=font.render("In-Game Menu",True,(255,255,255))
            screen.blit(t,(screen.get_width()//2 - t.get_width()//2,60))

            labels=["Resume","Reset Level","Select Level","Options","Exit"]
            ingame_buttons=layout_menu_buttons(labels)
            for label,rct in ingame_buttons:
                draw_button(screen, rct, label, font)

        elif game_state==STATE_USER_SELECT:
            back_rect=pygame.Rect(20,20,100,40)
            draw_button(screen, back_rect,"Back", font)

            labels=["New User"]
            user_buttons=layout_menu_buttons(labels)
            for label,rct in user_buttons:
                draw_button(screen, rct, label, font)

            t=font.render("Available Users:", True, (255,255,255))
            screen.blit(t,(screen.get_width()//2 - t.get_width()//2, 160))
            yy=200
            for usr in data["profiles"]:
                r=pygame.Rect(0,0,200,40)
                r.centerx=screen.get_width()//2
                r.y=yy
                yy+=50
                draw_button(screen, r, usr, font)

        elif game_state==STATE_NEW_USER:
            r=font.render("Enter username:",True,(255,255,255))
            r_rect=r.get_rect(center=(screen.get_width()//2,120))
            screen.blit(r,r_rect)

            new_user_input_rect=pygame.Rect(0,0,200,40)
            new_user_input_rect.center=(screen.get_width()//2,180)
            pygame.draw.rect(screen,(255,255,255),new_user_input_rect,2)
            txt_surf=font.render(new_user_text,True,(255,255,255))
            screen.blit(txt_surf,(new_user_input_rect.x+5,new_user_input_rect.y+5))

            create_rect=pygame.Rect(0,0,150,40)
            create_rect.center=(screen.get_width()//2,250)
            draw_button(screen, create_rect,"Create", font)

            if user_message:
                msg_s=font.render(user_message,True,(255,0,0))
                msg_rect=msg_s.get_rect(center=(screen.get_width()//2,300))
                screen.blit(msg_s,msg_rect)

        elif game_state==STATE_END_LEVEL:
            screen.blit(font.render("Level End Scoreboard", True,(255,255,255)),
                        (screen.get_width()//2-100,50))
            if profile:
                ls=profile["level_scores"]
                y=100
                total=0
                for lvl in range(1,MAX_LEVEL+1):
                    sc=ls[lvl]
                    line=f"Level {lvl} => {sc} points"
                    screen.blit(font.render(line,True,(255,255,255)),
                                (screen.get_width()//2-100,y))
                    y+=30
                    total+=sc
                screen.blit(font.render(f"Total = {total}", True, (255,255,0)),
                            (screen.get_width()//2-50,y))

            labels=["Next Level","Menu"]
            endlevel_buttons=layout_menu_buttons(labels)
            for label,rct in endlevel_buttons:
                draw_button(screen, rct, label, font)

        pygame.display.flip()
        clock.tick(60)

    save_profiles(data)
    pygame.quit()
    sys.exit()

if __name__=="__main__":
    main()
