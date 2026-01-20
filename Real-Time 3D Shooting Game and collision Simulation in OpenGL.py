from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

import math, random

# ----------------------- Window / camera -----------------------
WIN_W, WIN_H = 1000, 800
ASPECT = WIN_W / WIN_H
fovY = 120.0
GRID_LENGTH = 600
TILE = 60  # checker tile size

orbit_theta = math.radians(45)
cam_height = 280.0
follow_cam = False        # right click toggles
auto_follow_cam = False   # 'V' (only effective while cheat mode ON)

# ----------------------- Player / bullets ----------------------
player_x, player_y = 0.0, 0.0   # spawn at grid center
player_yaw = 0.0                # degrees (turn with A/D)
player_speed = 10.0
turn_speed = 4.0

bullets = []  # dict: {x,y,z,vx,vy,age,hit}
BULLET_SPEED = 40.0
BULLET_TTL = 80   # frames
fire_cooldown_frames = 8
cooldown = 0

life = 5
score = 0
missed = 0
game_over = False

# ----------------------- Enemies -------------------------------
ENEMY_N = 5
ENEMY_R = 22.0
enemies = []  # dict: {x,y,phase,alive}
enemy_speed = 1.5   # << Slower enemies

# ----------------------- Cheat mode ----------------------------
cheat_on = False
spin_speed = 4.0  # deg per frame

rand_var = 423
quad = None  # GLU quadric


# ----------------------- Helpers -------------------------------
def h2v(deg):
    a = math.radians(deg)
    return math.cos(a), math.sin(a)

def reset_game():
    global player_x, player_y, player_yaw, bullets, life, score, missed, game_over, cooldown, enemies
    player_x, player_y = 0.0, 0.0
    player_yaw = 0.0
    bullets.clear()
    life, score, missed = 5, 0, 0
    game_over = False
    cooldown = 0
    enemies.clear()
    for _ in range(ENEMY_N):
        spawn_enemy()

def spawn_enemy():
    # away from player and inside bounds
    while True:
        x = random.uniform(-GRID_LENGTH*0.75, GRID_LENGTH*0.75)
        y = random.uniform(-GRID_LENGTH*0.75, GRID_LENGTH*0.75)
        if math.hypot(x-player_x, y-player_y) > 250:
            break
    enemies.append(dict(x=x, y=y, phase=random.uniform(0, 6.28), alive=True))

def line_of_sight():
    """True if any enemy sits along player's aim (angle diff small) and in front."""
    px, py = player_x, player_y
    dirx, diry = h2v(player_yaw)
    for e in enemies:
        if not e["alive"]: 
            continue
        vx, vy = e["x"]-px, e["y"]-py
        dist = math.hypot(vx, vy)
        if dist < 40:
            return True
        dot = (vx*dirx + vy*diry) / (dist + 1e-6)
        if dot > math.cos(math.radians(6)):   # ~±6°
            return True
    return False


# ----------------------- Input --------------------------------
def keyboardListener(key, x, y):
    global player_x, player_y, player_yaw, cheat_on, auto_follow_cam
    global game_over
    k = key if isinstance(key, bytes) else bytes([key])

    if game_over:
        if k == b'r': reset_game()
        return

    if k == b'w':
        dx, dy = h2v(player_yaw)
        player_x += dx * player_speed
        player_y += dy * player_speed
    elif k == b's':
        dx, dy = h2v(player_yaw)
        player_x -= dx * player_speed
        player_y -= dy * player_speed
    elif k == b'a':
        player_yaw += turn_speed
    elif k == b'd':
        player_yaw -= turn_speed
    elif k == b'c':
        cheat_on = not cheat_on
    elif k == b'v':
        auto_follow_cam = not auto_follow_cam
    elif k == b'r':
        reset_game()

def specialKeyListener(key, x, y):
    global orbit_theta, cam_height
    if key == GLUT_KEY_LEFT:
        orbit_theta += math.radians(3)
    elif key == GLUT_KEY_RIGHT:
        orbit_theta -= math.radians(3)
    elif key == GLUT_KEY_UP:
        cam_height = min(cam_height + 12.0, 900.0)
    elif key == GLUT_KEY_DOWN:
        cam_height = max(cam_height - 12.0, 80.0)

def mouseListener(button, state, x, y):
    global follow_cam
    if state != GLUT_DOWN: 
        return
    if button == GLUT_LEFT_BUTTON:
        fire_bullet()
    elif button == GLUT_RIGHT_BUTTON:
        follow_cam = not follow_cam


# ----------------------- Camera --------------------------------
def compute_camera():
    if follow_cam:
        # Over-the-shoulder / first-personish. If 'V' and cheat_on -> even closer.
        behind = 120.0 if (cheat_on and auto_follow_cam) else 220.0
        px, py = player_x, player_y
        back = math.radians(player_yaw + 180)
        cx = px + math.cos(back) * behind
        cy = py + math.sin(back) * behind
        cz = 120.0 if (cheat_on and auto_follow_cam) else 180.0
        return (cx, cy, cz, px, py, 40.0, 0, 0, 1)
    else:
        cx = math.cos(orbit_theta) * 950.0
        cy = math.sin(orbit_theta) * 950.0
        cz = cam_height
        return (cx, cy, cz, 0.0, 0.0, 0.0, 0, 0, 1)

def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, ASPECT, 0.1, 3000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    cx, cy, cz, tx, ty, tz, ux, uy, uz = compute_camera()
    gluLookAt(cx, cy, cz, tx, ty, tz, ux, uy, uz)


# ----------------------- Game update ---------------------------
def fire_bullet():
    global cooldown
    if cooldown > 0 or game_over: 
        return
    dx, dy = h2v(player_yaw)
    sx = player_x + dx * 45.0
    sy = player_y + dy * 45.0
    bullets.append(dict(x=sx, y=sy, z=22.0, vx=dx*BULLET_SPEED, vy=dy*BULLET_SPEED, age=0, hit=False))
    cooldown = fire_cooldown_frames

def update_bullets():
    global missed
    i = 0
    while i < len(bullets):
        b = bullets[i]
        b["x"] += b["vx"]
        b["y"] += b["vy"]
        b["age"] += 1
        if (abs(b["x"]) > GRID_LENGTH+120 or abs(b["y"]) > GRID_LENGTH+120 or b["age"] > BULLET_TTL):
            if not b["hit"]:
                missed += 1
            bullets.pop(i)
        else:
            i += 1

def update_enemies():
    # move towards player; pulsate radius by phase
    for e in enemies:
        if not e["alive"]:
            continue
        vx, vy = (player_x - e["x"]), (player_y - e["y"])
        d = math.hypot(vx, vy) + 1e-6
        e["x"] += (vx / d) * enemy_speed
        e["y"] += (vy / d) * enemy_speed
        e["phase"] += 0.09

def enemy_radius_scale(e):
    # pulsate ~0.85..1.15
    return 1.0 + 0.15 * math.sin(e["phase"])

def check_collisions():
    global score, life
    # bullets vs enemies
    for b in bullets:
        if b["hit"]: 
            continue
        for e in enemies:
            if not e["alive"]:
                continue
            r = ENEMY_R * enemy_radius_scale(e)
            centers = [(e["x"], e["y"], r), (e["x"], e["y"], r*2.2)]
            for (cx, cy, cz) in centers:
                dx, dy, dz = b["x"]-cx, b["y"]-cy, b["z"]-cz
                if dx*dx + dy*dy + dz*dz <= (r*0.9)*(r*0.9):
                    e["alive"] = False
                    b["hit"] = True
                    score += 1
    # enemies touching player
    for e in enemies:
        if not e["alive"]:
            continue
        dx, dy = e["x"]-player_x, e["y"]-player_y
        if dx*dx + dy*dy <= (ENEMY_R*1.6)*(ENEMY_R*1.6):
            life -= 1
            e["alive"] = False

    # respawn to keep 5 alive
    alive = sum(1 for e in enemies if e["alive"])
    for _ in range(ENEMY_N - alive):
        spawn_enemy()

def logic():
    global cooldown, player_yaw, game_over
    if game_over:
        return
    if cheat_on:
        player_yaw += spin_speed
        if line_of_sight():
            fire_bullet()
    if cooldown > 0:
        cooldown -= 1
    update_bullets()
    update_enemies()
    check_collisions()
    if life <= 0 or missed >= 10:
        game_over = True


# ----------------------- Drawing -------------------------------
def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1,1,1)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text: glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_checker():
    half = GRID_LENGTH
    cols = int((half*2)//TILE)
    start = -half
    glBegin(GL_QUADS)
    for i in range(cols):
        for j in range(cols):
            x0 = start + i*TILE; x1 = x0 + TILE
            y0 = start + j*TILE; y1 = y0 + TILE
            if (i + j) % 2 == 0:
                glColor3f(1.0, 1.0, 1.0)
            else:
                glColor3f(0.75, 0.65, 0.95)
            glVertex3f(x0, y0, 0); glVertex3f(x1, y0, 0)
            glVertex3f(x1, y1, 0); glVertex3f(x0, y1, 0)
    glEnd()

def draw_walls():
    half = GRID_LENGTH
    h = 120.0
    # top (cyan)
    glColor3f(0.0, 1.0, 1.0)
    glBegin(GL_QUADS)
    glVertex3f(-half,  half, 0); glVertex3f( half,  half, 0)
    glVertex3f( half,  half, h); glVertex3f(-half,  half, h)
    glEnd()
    # left (blue)
    glColor3f(0.0, 0.0, 1.0)
    glBegin(GL_QUADS)
    glVertex3f(-half, -half, 0); glVertex3f(-half,  half, 0)
    glVertex3f(-half,  half, h); glVertex3f(-half, -half, h)
    glEnd()
    # right (green)
    glColor3f(0.0, 1.0, 0.0)
    glBegin(GL_QUADS)
    glVertex3f( half, -half, 0); glVertex3f( half,  half, 0)
    glVertex3f( half,  half, h); glVertex3f( half, -half, h)
    glEnd()
    # bottom (sky-ish blue)
    glColor3f(0.1, 0.5, 1.0)
    glBegin(GL_QUADS)
    glVertex3f(-half, -half, 0); glVertex3f( half, -half, 0)
    glVertex3f( half, -half, h); glVertex3f(-half, -half, h)
    glEnd()

def draw_player_model(lying=False):
    glPushMatrix()
    glTranslatef(player_x, player_y, 0)
    glRotatef(player_yaw, 0, 0, 1)

    if lying:
        glRotatef(90, 0, 1, 0)  # lie on side

    # Torso (cuboid)
    glPushMatrix()
    glColor3f(0.4, 0.7, 0.4)
    glTranslatef(0, 0, 40)
    glScalef(25, 18, 50)
    glutSolidCube(1)
    glPopMatrix()

    # Head (sphere)
    glPushMatrix()
    glColor3f(1.0, 0.85, 0.7)
    glTranslatef(0, 0, 80)
    gluSphere(quad, 12, 16, 16)
    glPopMatrix()

    # Shoulders (small cubes)
    for sgn in (-1, 1):
        glPushMatrix()
        glColor3f(0.9, 0.9, 0.9)
        glTranslatef(0, sgn*14, 55)
        glScalef(8, 8, 8)
        glutSolidCube(1)
        glPopMatrix()

    # Arms (cylinders) + hands (small spheres)
    for sgn in (-1, 1):
        glPushMatrix()
        glColor3f(0.9, 0.9, 0.9)
        glTranslatef(10, sgn*14, 55)
        glRotatef(90, 0, 1, 0)
        gluCylinder(quad, 3.5, 3.5, 18, 10, 1)
        glPopMatrix()

        glPushMatrix()
        glColor3f(1.0, 0.85, 0.7)
        glTranslatef(18, sgn*14, 55)
        gluSphere(quad, 3.8, 10, 10)
        glPopMatrix()

    # Legs (cones)
    for sgn in (-1, 1):
        glPushMatrix()
        glColor3f(0.2, 0.2, 1.0)
        glTranslatef(-4, sgn*6, 18)
        glRotatef(-90, 1, 0, 0)
        glRotatef(15*sgn, 0, 1, 0)
        gluCylinder(quad, 5.5, 0.5, 28, 10, 1)
        glPopMatrix()

    # Gun (long cone pointing forward)
    glPushMatrix()
    glColor3f(0.85, 0.85, 0.9)
    glTranslatef(20, 0, 58)
    glRotatef(90, 0, 1, 0)  # orient along +X
    gluCylinder(quad, 3.0, 0.2, 60, 12, 1)
    glPopMatrix()

    glPopMatrix()

def draw_bullets():
    glColor3f(1.0, 1.0, 0.0)
    for b in bullets:
        glPushMatrix()
        glTranslatef(b["x"], b["y"], b["z"])
        glScalef(6, 6, 6)
        glutSolidCube(1)
        glPopMatrix()

def draw_enemy(e):
    if not e["alive"]: 
        return
    s = enemy_radius_scale(e)
    r = ENEMY_R * s
    glPushMatrix()
    glTranslatef(e["x"], e["y"], r)
    glColor3f(1.0, 0.15, 0.15)  # red
    gluSphere(quad, r, 16, 16)
    glTranslatef(0, 0, r*1.25)
    glColor3f(0.0, 0.0, 0.0)   # black pupil cap
    gluSphere(quad, r*0.5, 12, 12)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(e["x"], e["y"], r*2.2)
    glColor3f(1.0, 0.2, 0.2)
    gluSphere(quad, r, 16, 16)
    glPopMatrix()

def draw_enemies():
    for e in enemies: 
        draw_enemy(e)


# ----------------------- Frame funcs ---------------------------
def idle():
    logic()
    glutPostRedisplay()

def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glViewport(0, 0, WIN_W, WIN_H)
    setupCamera()

    draw_checker()
    draw_walls()
    draw_player_model(lying=game_over)
    draw_bullets()
    draw_enemies()

    # HUD
    draw_text(20, WIN_H-30, f"Player Life Remaining: {life}")
    draw_text(20, WIN_H-55, f"Game Score: {score}")
    draw_text(20, WIN_H-80, f"Player Bullet Missed: {missed}")
    if cheat_on:
        draw_text(20, WIN_H-105, "Cheat Mode: ON   (C to toggle)")
    if game_over:
        draw_text(20, WIN_H-135, "GAME OVER - Press R to Restart")

    glutSwapBuffers()


# ----------------------- Main ---------------------------------
def main():
    global quad
    random.seed(42)
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H)
    glutInitWindowPosition(30, 30)
    glutCreateWindow(b"Bullet Frenzy - 3D Lab Assignment")

    quad = gluNewQuadric()

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    reset_game()
    glutMainLoop()

if __name__ == "__main__":
    main()