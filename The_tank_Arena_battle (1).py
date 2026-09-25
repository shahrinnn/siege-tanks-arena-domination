import sys, math, random, json, os, datetime

from OpenGL.GL   import *
from OpenGL.GLUT import *
from OpenGL.GLU  import *

SCORE_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "siege_tanks_scores.json")
MAX_RECORDS = 10

def _load_scores():
    try:
        if os.path.exists(SCORE_FILE):
            with open(SCORE_FILE, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []

def _save_scores(records):
    try:
        records_sorted = sorted(records, key=lambda r: r["score"], reverse=True)
        with open(SCORE_FILE, "w") as f:
            json.dump(records_sorted[:MAX_RECORDS], f, indent=2)
    except Exception as e:
        print(f"[WARN] Could not save scores: {e}")

def record_game_result(result_str):
    elapsed = 0.0
    try:
        elapsed = (glutGet(GLUT_ELAPSED_TIME) / 1000.0) - _session_start_t
    except Exception:
        pass
    entry = {
        "date"      : datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "arena"     : ARENAS[arena_sel]["name"],
        "result"    : result_str,
        "score"     : global_score,
        "kills"     : global_kills,
        "captures"  : player.captures,
        "waves"     : wave,
        "round"     : current_round,
        "playtime_s": int(elapsed),
    }
    records = _load_scores()
    records.append(entry)
    _save_scores(records)

def get_high_score():
    records = _load_scores()
    if not records:
        return 0
    return max(r["score"] for r in records)

def fmt_time(seconds):
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"

_session_start_t = 0.0
_result_recorded = False

WIN_W, WIN_H = 1100, 800
ARENA  = 750
WALL_T = 22

# game states
S_MENU      = 0
S_ARENA     = 1
S_PLAY      = 2
S_PAUSE     = 3
S_OVER      = 4
S_WIN       = 5
S_INSTR     = 6
S_SCORES    = 7
S_LEVELUP   = 8
S_GAMECLEAR = 9

game_state = S_MENU
menu_sel   = 0
arena_sel  = 0

MAX_ROUNDS     = 5
current_round  = 1
levelup_timer  = 0.0
LEVELUP_HOLD   = 5.0

ROUND_CONFIG = {
    1: {"waves": 3, "enemy_hp_mult": 1.0, "enemy_spd_mult": 1.0, "enemy_dmg_mult": 1.0,
        "wave_size_base": 3, "label": "ROUND 1 — Boot Camp",    "color": (0.3, 1.0, 0.3)},
    2: {"waves": 4, "enemy_hp_mult": 1.3, "enemy_spd_mult": 1.1, "enemy_dmg_mult": 1.2,
        "wave_size_base": 4, "label": "ROUND 2 — Escalation",   "color": (0.7, 1.0, 0.2)},
    3: {"waves": 4, "enemy_hp_mult": 1.7, "enemy_spd_mult": 1.2, "enemy_dmg_mult": 1.5,
        "wave_size_base": 5, "label": "ROUND 3 — Storm Front",  "color": (1.0, 0.8, 0.1)},
    4: {"waves": 5, "enemy_hp_mult": 2.2, "enemy_spd_mult": 1.3, "enemy_dmg_mult": 1.9,
        "wave_size_base": 6, "label": "ROUND 4 — Iron Siege",   "color": (1.0, 0.5, 0.1)},
    5: {"waves": 3, "enemy_hp_mult": 2.8, "enemy_spd_mult": 1.4, "enemy_dmg_mult": 2.4,
        "wave_size_base": 5, "label": "ROUND 5 — BOSS BATTLE",  "color": (1.0, 0.2, 0.2)},
}

round_waves_needed  = 0
round_waves_cleared = 0

# upgrade system
upgrade_tokens   = 0
upgrade_menu_sel = 0
UPGRADES = [
    {"id": "hp",      "label": "+30 Max HP",          "cost": 1},
    {"id": "ammo",    "label": "+5 Max Ammo",          "cost": 1},
    {"id": "shield",  "label": "-3s Shield Cooldown",  "cost": 1},
    {"id": "missile", "label": "-2s Missile Cooldown", "cost": 1},
    {"id": "speed",   "label": "+0.5 Tank Speed Bonus","cost": 1},
    {"id": "dmg",     "label": "+5 Bullet Damage",     "cost": 1},
]
player_upgrades = {"hp": 0, "ammo": 0, "shield": 0, "missile": 0, "speed": 0, "dmg": 0}

fovY         = 70
cam_angle    = 0.0
cam_pitch    = 42.0
cam_dist     = 420.0
first_person = False

ARENAS = [
    {"name":"Desert",  "fa":(0.72,0.62,0.30),"fb":(0.60,0.50,0.22),
     "wall":(0.75,0.60,0.30),"sky":(0.80,0.65,0.30),
     "trunk":(0.55,0.38,0.18),"leaves":(0.70,0.60,0.15)},
    {"name":"Ice",     "fa":(0.65,0.80,0.95),"fb":(0.52,0.68,0.85),
     "wall":(0.80,0.90,1.00),"sky":(0.55,0.70,0.90),
     "trunk":(0.55,0.70,0.85),"leaves":(0.75,0.90,1.00)},
    {"name":"Volcano", "fa":(0.22,0.12,0.08),"fb":(0.30,0.16,0.06),
     "wall":(0.38,0.20,0.08),"sky":(0.55,0.18,0.04),
     "trunk":(0.28,0.14,0.06),"leaves":(0.60,0.18,0.05)},
    {"name":"Forest",  "fa":(0.15,0.35,0.12),"fb":(0.10,0.26,0.08),
     "wall":(0.18,0.30,0.10),"sky":(0.18,0.32,0.12),
     "trunk":(0.28,0.18,0.08),"leaves":(0.12,0.48,0.10)},
]

TANK_TYPES = {
    "light":    {"speed":5.0, "dmg":10, "hp":60,  "col":(0.20,0.90,0.20), "label":"Light"},
    "balanced": {"speed":3.5, "dmg":20, "hp":100, "col":(0.25,0.55,1.00), "label":"Balanced"},
    "heavy":    {"speed":2.0, "dmg":35, "hp":180, "col":(0.95,0.42,0.10), "label":"Heavy"},
}
TT = ["light", "balanced", "heavy"]

PLAYER_BASE = (-620, -620)
ENEMY_BASE  = ( 620,  620)
BASE_R      = 70

VISION_RANGE = 420

SHIELD_DUR  = 5.0
SHIELD_CD   = 15.0
MISSILE_CD  = 8.0

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def dist2(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)

def wall_clamp(x, y, margin=26):
    return clamp(x, -ARENA+margin, ARENA-margin), clamp(y, -ARENA+margin, ARENA-margin)

def line_blocked_by_tree(x1, y1, x2, y2):
    for t in trees:
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            continue
        t_proj = ((t.x - x1)*dx + (t.y - y1)*dy) / (dx*dx + dy*dy)
        t_proj = clamp(t_proj, 0.0, 1.0)
        cx = x1 + t_proj * dx
        cy = y1 + t_proj * dy
        if dist2(cx, cy, t.x, t.y) < Tree.TRUNK_R + 6:
            return True
    return False

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18, color=(1,1,1)):
    was = glIsEnabled(GL_DEPTH_TEST)
    glDisable(GL_DEPTH_TEST)
    glColor3f(*color)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    if was:
        glEnable(GL_DEPTH_TEST)

def draw_text_big(x, y, text, color=(1,1,1)):
    draw_text(x, y, text, GLUT_BITMAP_TIMES_ROMAN_24, color)

def draw_rect2d(x, y, w, h, col):
    was = glIsEnabled(GL_DEPTH_TEST)
    glDisable(GL_DEPTH_TEST)
    glColor3f(*col)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glBegin(GL_QUADS)
    glVertex2f(x,     y)
    glVertex2f(x + w, y)
    glVertex2f(x + w, y + h)
    glVertex2f(x,     y + h)
    glEnd()
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    if was:
        glEnable(GL_DEPTH_TEST)


class Bullet:
    SPD    = 13.0
    RADIUS = 6
    RANGE  = 1800

    def __init__(self, x, y, angle_rad, owner="player", damage=20, missile=False):
        self.x       = x
        self.y       = y
        self.vx      = math.cos(angle_rad) * self.SPD
        self.vy      = math.sin(angle_rad) * self.SPD
        self.owner   = owner
        self.damage  = damage
        self.missile = missile
        self.radius  = 12 if missile else self.RADIUS
        self.dist    = 0.0
        self.alive   = True

    def update(self):
        self.x    += self.vx
        self.y    += self.vy
        self.dist += self.SPD
        if self.dist > self.RANGE or abs(self.x) > ARENA or abs(self.y) > ARENA:
            self.alive = False

bullets = []


class Explosion:
    def __init__(self, x, y, big=False):
        self.x     = x
        self.y     = y
        self.big   = big
        self.max   = 0.85 if big else 0.50
        self.timer = self.max

    @property
    def alive(self):
        return self.timer > 0

    def update(self, dt):
        self.timer -= dt

explosions = []


class Tree:
    TRUNK_R  = 10
    BULLET_R = 12
    CANOPY_R = 38

    def __init__(self, x, y):
        self.x = x
        self.y = y

trees = []


class Crate:
    SZ = 34

    def __init__(self, x, y):
        self.x     = x
        self.y     = y
        self.alive = True


class Bomb:
    RADIUS    = 20
    STEP_R    = 38
    EXPLODE_R = 160

    def __init__(self, x, y):
        self.x         = x
        self.y         = y
        self.alive     = True
        self.triggered = False
        self.fuse      = 1.5

    def trigger(self):
        if not self.triggered:
            self.triggered = True

crates = []
bombs  = []


def _pos_free_for_tree(x, y, margin=80):
    for bx, by in [PLAYER_BASE, ENEMY_BASE]:
        if dist2(x, y, bx, by) < margin + BASE_R:
            return False
    for t in trees:
        if dist2(x, y, t.x, t.y) < margin:
            return False
    for c in crates:
        if dist2(x, y, c.x, c.y) < margin:
            return False
    for b in bombs:
        if dist2(x, y, b.x, b.y) < margin:
            return False
    return True

def _obs_free(x, y, margin=70):
    for bx, by in [PLAYER_BASE, ENEMY_BASE]:
        if dist2(x, y, bx, by) < margin + BASE_R + 20:
            return False
    for c in crates:
        if dist2(x, y, c.x, c.y) < margin:
            return False
    for b in bombs:
        if dist2(x, y, b.x, b.y) < margin:
            return False
    for t in trees:
        if dist2(x, y, t.x, t.y) < margin:
            return False
    return True

def generate_obstacles():
    global crates, bombs, trees
    crates = []
    bombs  = []
    trees  = []

    for _ in range(600):
        if len(trees) >= 18:
            break
        x = random.uniform(-ARENA + 80, ARENA - 80)
        y = random.uniform(-ARENA + 80, ARENA - 80)
        if _pos_free_for_tree(x, y, 90):
            trees.append(Tree(x, y))

    for _ in range(600):
        if len(crates) >= 16:
            break
        x = random.uniform(-ARENA + 80, ARENA - 80)
        y = random.uniform(-ARENA + 80, ARENA - 80)
        if _obs_free(x, y, 72):
            crates.append(Crate(x, y))

    for _ in range(600):
        if len(bombs) >= 8:
            break
        x = random.uniform(-ARENA + 80, ARENA - 80)
        y = random.uniform(-ARENA + 80, ARENA - 80)
        if _obs_free(x, y, 85):
            bombs.append(Bomb(x, y))


class Player:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x          = -500.0
        self.y          = -500.0
        self.angle      = 0.0
        self.turret_a   = 0.0
        self.tank_type  = "balanced"
        self.hp         = TANK_TYPES["balanced"]["hp"]
        self.ammo       = 10
        self.max_ammo   = 10
        self.reloading  = False
        self.reload_t   = 0.0
        self.has_flag   = False
        self.captures   = 0
        self.alive      = True
        self.move_dir   = 0
        self.rot_dir    = 0
        self.shield_on  = False
        self.shield_t   = 0.0
        self.shield_cd  = 0.0
        self.missile_cd = 0.0
        self.cheat_aim  = False
        self.kills      = 0
        self.score      = 0
        self._speed_bonus = 0.0
        self._dmg_bonus   = 0

    def apply_upgrades(self):
        # re-apply all upgrades after a reset or round start
        up = player_upgrades
        bonus_hp  = up["hp"]   * 30
        bonus_ammo = up["ammo"] * 5
        self.max_ammo = 10 + bonus_ammo
        self.ammo     = self.max_ammo
        base_hp       = TANK_TYPES[self.tank_type]["hp"]
        self.hp       = base_hp + bonus_hp
        self._speed_bonus = up["speed"] * 0.5
        self._dmg_bonus   = up["dmg"]   * 5
        self.shield_cd  = max(0, SHIELD_CD  - up["shield"]  * 3)
        self.missile_cd = max(0, MISSILE_CD - up["missile"] * 2)

    @property
    def speed(self):
        s = TANK_TYPES[self.tank_type]["speed"] + self._speed_bonus
        return s * (0.6 if self.has_flag else 1.0)

    @property
    def dmg(self):
        return TANK_TYPES[self.tank_type]["dmg"] + self._dmg_bonus

    @property
    def max_hp(self):
        return TANK_TYPES[self.tank_type]["hp"] + player_upgrades["hp"] * 30

    @property
    def col(self):
        return TANK_TYPES[self.tank_type]["col"]

    def switch_type(self):
        i = TT.index(self.tank_type)
        self.tank_type = TT[(i + 1) % 3]
        self.hp = min(self.hp, self.max_hp)

    def _blocked_by_tree(self, nx, ny):
        for t in trees:
            if dist2(nx, ny, t.x, t.y) < Tree.TRUNK_R + 24:
                return True
        return False

    def update(self, dt):
        if not self.alive:
            return
        if self.move_dir:
            rad = math.radians(self.angle)
            nx  = self.x + math.cos(rad) * self.speed * self.move_dir
            ny  = self.y + math.sin(rad) * self.speed * self.move_dir
            nx, ny  = wall_clamp(nx, ny)
            blocked = False
            for c in crates:
                if c.alive and dist2(nx, ny, c.x, c.y) < Crate.SZ + 22:
                    blocked = True
                    break
            if not blocked and self._blocked_by_tree(nx, ny):
                blocked = True
            if not blocked:
                self.x = nx
                self.y = ny
        self.angle += self.rot_dir * 2.5
        if self.reloading:
            self.reload_t -= dt
            if self.reload_t <= 0:
                self.ammo      = self.max_ammo
                self.reloading = False
        if self.shield_on:
            self.shield_t -= dt
            if self.shield_t <= 0:
                self.shield_on = False
        if self.shield_cd > 0:
            self.shield_cd -= dt
        if self.missile_cd > 0:
            self.missile_cd -= dt

    def fire(self):
        if self.ammo <= 0 or self.reloading or not self.alive:
            return None
        self.ammo -= 1
        a = math.radians(self.angle + self.turret_a)
        return Bullet(self.x + math.cos(a)*44, self.y + math.sin(a)*44, a, "player", self.dmg)

    def fire_missile(self):
        if self.missile_cd > 0 or not self.alive:
            return None
        self.missile_cd = max(1.0, MISSILE_CD - player_upgrades["missile"] * 2)
        a = math.radians(self.angle + self.turret_a)
        return Bullet(self.x + math.cos(a)*44, self.y + math.sin(a)*44, a, "player", self.dmg*4, True)

    def shield(self):
        cd_max = max(4.0, SHIELD_CD - player_upgrades["shield"] * 3)
        if self.shield_cd <= 0 and not self.shield_on:
            self.shield_on = True
            self.shield_t  = SHIELD_DUR
            self.shield_cd = cd_max

    def reload(self):
        if not self.reloading and self.ammo < self.max_ammo:
            self.reloading = True
            self.reload_t  = 3.0

    def take_damage(self, d):
        if self.shield_on:
            d = max(1, d // 4)
        self.hp -= d
        if self.hp <= 0:
            self.hp    = 0
            self.alive = False
            if self.has_flag:
                self.has_flag = False
                flag.player_drops()

player = Player()


class Ally:
    RADIUS   = 25
    SPD      = 3.2
    SHOOT_CD = 2.0
    SHOOT_R  = 400

    def __init__(self):
        self.x       = -560.0
        self.y       = -380.0
        self.angle   = 0.0
        self.hp      = 80
        self.max_hp  = 80
        self.alive   = True
        self.shoot_t = 1.0
        self.kills   = 0

    def _blocked_by_tree(self, nx, ny):
        for t in trees:
            if dist2(nx, ny, t.x, t.y) < Tree.TRUNK_R + 24:
                return True
        return False

    def update(self, dt):
        if not self.alive:
            return
        al = [e for e in enemies if e.alive]
        if al:
            tgt = min(al, key=lambda e: dist2(self.x, self.y, e.x, e.y))
            dx  = tgt.x - self.x
            dy  = tgt.y - self.y
            d   = math.hypot(dx, dy)
            if d > 200:
                self.angle = math.degrees(math.atan2(dy, dx))
                nx = self.x + (dx / d) * self.SPD
                ny = self.y + (dy / d) * self.SPD
                nx, ny  = wall_clamp(nx, ny)
                blocked = any(c.alive and dist2(nx, ny, c.x, c.y) < Crate.SZ + 22 for c in crates)
                if not blocked:
                    blocked = self._blocked_by_tree(nx, ny)
                if not blocked:
                    self.x = nx
                    self.y = ny
            self.shoot_t -= dt
            if self.shoot_t <= 0 and d < self.SHOOT_R:
                self.shoot_t = self.SHOOT_CD
                a = math.atan2(tgt.y - self.y, tgt.x - self.x)
                bullets.append(Bullet(self.x + math.cos(a)*38, self.y + math.sin(a)*38, a, "ally", 18))
        else:
            dx = player.x - self.x
            dy = player.y - self.y
            d  = math.hypot(dx, dy)
            if d > 160:
                self.angle = math.degrees(math.atan2(dy, dx))
                nx = self.x + (dx / d) * self.SPD
                ny = self.y + (dy / d) * self.SPD
                nx, ny = wall_clamp(nx, ny)
                self.x = nx
                self.y = ny

    def take_damage(self, d):
        self.hp -= d
        if self.hp <= 0:
            self.hp    = 0
            self.alive = False

ally = Ally()


class DualFlag:
    def __init__(self):
        self.reset()

    def reset(self):
        self.gx, self.gy  = ENEMY_BASE
        self.gold_at_base = True
        self.player_has   = False
        self.bx, self.by  = PLAYER_BASE
        self.blue_at_base = True
        self.enemy_has    = False
        self.e_carrier    = None

    def player_drops(self):
        self.gx           = player.x
        self.gy           = player.y
        self.gold_at_base = False
        self.player_has   = False

    def enemy_drops(self):
        if self.e_carrier:
            self.bx = self.e_carrier.x
            self.by = self.e_carrier.y
        self.blue_at_base = False
        self.enemy_has    = False
        self.e_carrier    = None

flag = DualFlag()


class Boss:
    # big boss tank that appears on round 5
    RADIUS   = 55
    SHOOT_CD = 1.2
    SHOOT_R  = 600
    PHASE2_HP_RATIO = 0.5

    def __init__(self, rnd):
        self.x        = 500.0
        self.y        = 500.0
        self.angle    = 180.0
        self.hp       = int(1200 * (1 + (rnd - 5) * 0.3))
        self.max_hp   = self.hp
        self.speed    = 1.8
        self.damage   = 35
        self.alive    = True
        self.shoot_t  = 0.5
        self.phase    = 1
        self.has_flag = False
        self.score    = 0
        self.kills    = 0
        self._burst_count = 0
        self._burst_t     = 0.0
        self._is_bursting = False
        self._charge_t    = 0.0
        self._charging    = False
        self._charge_vx   = 0.0
        self._charge_vy   = 0.0
        self._charge_dur  = 0.0
        self._circle_t    = 0.0
        self._circle_dir  = 1

    @property
    def hp_ratio(self):
        return self.hp / self.max_hp

    def _blocked_by_tree(self, nx, ny):
        for t in trees:
            if dist2(nx, ny, t.x, t.y) < Tree.TRUNK_R + 30:
                return True
        return False

    def update(self, dt):
        if not self.alive:
            return

        # check phase transition
        if self.phase == 1 and self.hp_ratio < self.PHASE2_HP_RATIO:
            self.phase = 2
            explosions.append(Explosion(self.x, self.y, big=True))
            # burst of 8 bullets when entering phase 2
            for i in range(8):
                a = math.radians(i * 45)
                bullets.append(Bullet(self.x, self.y, a, "enemy", self.damage))

        # charge movement
        if self._charging:
            self._charge_dur -= dt
            if self._charge_dur <= 0:
                self._charging = False
            else:
                nx = self.x + self._charge_vx * dt * 280
                ny = self.y + self._charge_vy * dt * 280
                nx, ny = wall_clamp(nx, ny, 60)
                if not self._blocked_by_tree(nx, ny):
                    self.x, self.y = nx, ny
        else:
            # normal movement toward player or ally
            targets = []
            if player.alive:
                targets.append((player.x, player.y))
            if ally.alive:
                targets.append((ally.x, ally.y))
            if targets:
                tx, ty = min(targets, key=lambda p: dist2(self.x, self.y, p[0], p[1]))
                dx = tx - self.x
                dy = ty - self.y
                d  = math.hypot(dx, dy)
                if d > 10:
                    spd = self.speed * (1.4 if self.phase == 2 else 1.0)
                    self.angle = math.degrees(math.atan2(dy, dx))
                    if self.phase == 2:
                        # circle strafe in phase 2
                        self._circle_t += dt
                        if self._circle_t > 3.5:
                            self._circle_t = 0.0
                            self._circle_dir *= -1
                        perp_a = math.atan2(dy, dx) + math.pi/2 * self._circle_dir
                        nx = self.x + (math.cos(math.atan2(dy,dx)) * 0.6 + math.cos(perp_a) * 0.4) * spd
                        ny = self.y + (math.sin(math.atan2(dy,dx)) * 0.6 + math.sin(perp_a) * 0.4) * spd
                    else:
                        nx = self.x + (dx/d) * spd
                        ny = self.y + (dy/d) * spd
                    nx, ny = wall_clamp(nx, ny, 60)
                    if not self._blocked_by_tree(nx, ny):
                        self.x, self.y = nx, ny

            # charge attack only in phase 2
            if self.phase == 2:
                self._charge_t -= dt
                if self._charge_t <= 0 and targets:
                    tx, ty = min(targets, key=lambda p: dist2(self.x,self.y,p[0],p[1]))
                    dx = tx - self.x
                    dy = ty - self.y
                    d  = math.hypot(dx, dy)
                    if d > 0:
                        self._charge_vx  = dx / d
                        self._charge_vy  = dy / d
                        self._charging   = True
                        self._charge_dur = 0.55
                        self._charge_t   = 5.0

        # shooting
        self.shoot_t -= dt
        if self.shoot_t <= 0:
            targets = []
            if player.alive:
                targets.append((player.x, player.y))
            if ally.alive:
                targets.append((ally.x, ally.y))
            if targets:
                tx, ty = min(targets, key=lambda p: dist2(self.x,self.y,p[0],p[1]))
                d = dist2(self.x, self.y, tx, ty)
                if d < self.SHOOT_R:
                    a = math.atan2(ty - self.y, tx - self.x)
                    if self.phase == 2:
                        # triple shot spread in phase 2
                        for spread in [-0.15, 0, 0.15]:
                            bullets.append(Bullet(self.x + math.cos(a+spread)*60,
                                                  self.y + math.sin(a+spread)*60,
                                                  a + spread, "enemy", self.damage))
                    else:
                        bullets.append(Bullet(self.x + math.cos(a)*60,
                                              self.y + math.sin(a)*60,
                                              a, "enemy", self.damage))
                    self.shoot_t = self.SHOOT_CD * (0.65 if self.phase == 2 else 1.0)

    def take_damage(self, d):
        self.hp -= d
        if self.hp <= 0:
            self.hp    = 0
            self.alive = False

boss = None


class Enemy:
    RADIUS   = 25
    SHOOT_CD = 2.5
    SHOOT_R  = 420

    def __init__(self, wave, idx=0):
        edge = random.choice(["T", "B", "L", "R"])
        off  = random.uniform(-ARENA + 70, ARENA - 70)
        if edge == "T":
            self.x, self.y = off, ARENA - 40
        elif edge == "B":
            self.x, self.y = off, -ARENA + 40
        elif edge == "L":
            self.x, self.y = -ARENA + 40, off
        else:
            self.x, self.y = ARENA - 40, off

        cfg = ROUND_CONFIG[current_round]
        d   = (1 + (wave - 1) * 0.15) * cfg["enemy_hp_mult"]
        self.hp       = int(55 * d)
        self.max_hp   = self.hp
        self.speed    = (1.6 + wave * 0.15) * cfg["enemy_spd_mult"]
        self.damage   = int(8 * d * cfg["enemy_dmg_mult"])
        self.angle    = 0.0
        self.shoot_t  = random.uniform(0, self.SHOOT_CD)
        self.alive    = True
        self.has_flag = False
        self.kills    = 0
        self.score    = 0

        self._wander_x = random.uniform(-ARENA + 80, ARENA - 80)
        self._wander_y = random.uniform(-ARENA + 80, ARENA - 80)
        self._wander_t = 0.0

        roles     = ["chaser", "chaser", "guard", "flag_stealer"]
        self.role = roles[idx % len(roles)]

    def _pick_target(self):
        if self.has_flag:
            return ENEMY_BASE[0], ENEMY_BASE[1], False
        if self.role == "flag_stealer" and not flag.enemy_has:
            if not flag.blue_at_base:
                fx, fy = flag.bx, flag.by
            else:
                fx, fy = PLAYER_BASE
            return fx, fy, False
        if self.role == "guard":
            visible = self._visible_targets()
            if visible:
                tx, ty, _ = min(visible, key=lambda c: c[2])
                return tx, ty, True
            return ENEMY_BASE[0], ENEMY_BASE[1], False
        visible = self._visible_targets()
        if visible:
            tx, ty, _ = min(visible, key=lambda c: c[2])
            return tx, ty, True
        return self._wander_x, self._wander_y, False

    def _visible_targets(self):
        result = []
        if player.alive:
            d = dist2(self.x, self.y, player.x, player.y)
            if d < VISION_RANGE and not line_blocked_by_tree(self.x, self.y, player.x, player.y):
                result.append((player.x, player.y, d))
        if ally.alive:
            d = dist2(self.x, self.y, ally.x, ally.y)
            if d < VISION_RANGE and not line_blocked_by_tree(self.x, self.y, ally.x, ally.y):
                result.append((ally.x, ally.y, d))
        return result

    def _blocked_by_tree(self, nx, ny):
        for t in trees:
            if dist2(nx, ny, t.x, t.y) < Tree.TRUNK_R + 24:
                return True
        return False

    def update(self, dt):
        if not self.alive:
            return
        self._wander_t -= dt
        if self._wander_t <= 0:
            self._wander_t = random.uniform(2.5, 5.0)
            self._wander_x = random.uniform(-ARENA + 80, ARENA - 80)
            self._wander_y = random.uniform(-ARENA + 80, ARENA - 80)

        tx, ty, is_combat = self._pick_target()
        dx = tx - self.x
        dy = ty - self.y
        d  = math.hypot(dx, dy)

        if d > 5:
            self.angle = math.degrees(math.atan2(dy, dx))
            nx = self.x + (dx / d) * self.speed
            ny = self.y + (dy / d) * self.speed
            nx, ny  = wall_clamp(nx, ny)
            blocked = any(c.alive and dist2(nx, ny, c.x, c.y) < Crate.SZ + 22 for c in crates)
            if not blocked:
                blocked = self._blocked_by_tree(nx, ny)
            if not blocked:
                self.x = nx
                self.y = ny

        self.shoot_t -= dt
        if self.shoot_t <= 0 and d < self.SHOOT_R and is_combat:
            visible = self._visible_targets()
            if visible:
                sx, sy, _ = min(visible, key=lambda c: c[2])
                self.shoot_t = self.SHOOT_CD
                a = math.atan2(sy - self.y, sx - self.x)
                bullets.append(Bullet(
                    self.x + math.cos(a) * 38,
                    self.y + math.sin(a) * 38,
                    a, "enemy", self.damage
                ))

    def take_damage(self, d):
        self.hp -= d
        if self.hp <= 0:
            self.hp    = 0
            self.alive = False
            if self.has_flag:
                self.has_flag = False
                flag.enemy_drops()

enemies = []

wave        = 1
wave_delay  = 0.0
WAVE_DELAY  = 4.0
wave_active = False
global_score = 0
global_kills = 0


def start_wave(w):
    global enemies, wave_active, boss
    cfg = ROUND_CONFIG[current_round]

    if current_round == MAX_ROUNDS:
        # round 5 wave 3 is the boss wave
        if w == 3:
            enemies     = []
            boss        = Boss(current_round)
            wave_active = True
            return
        count = cfg["wave_size_base"] + (w - 1) * 2
    else:
        count = cfg["wave_size_base"] + (w - 1) * 2

    enemies     = [Enemy(w, i) for i in range(count)]
    wave_active = True

def _all_threats_dead():
    # returns True when all enemies and boss are dead
    e_dead = all(not e.alive for e in enemies)
    b_dead = (boss is None or not boss.alive)
    return e_dead and b_dead

def check_wave_done():
    global wave, wave_delay, wave_active, round_waves_cleared
    if wave_active and _all_threats_dead():
        wave_active         = False
        round_waves_cleared += 1
        wave_delay          = WAVE_DELAY
        wave               += 1

def check_collisions():
    global global_score, global_kills

    for b in bullets:
        if not b.alive:
            continue
        if b.owner in ("player", "ally"):
            # check enemy hits
            for e in enemies:
                if not e.alive:
                    continue
                if dist2(b.x, b.y, e.x, e.y) < Enemy.RADIUS + b.radius:
                    e.take_damage(b.damage)
                    b.alive = False
                    if not e.alive:
                        explosions.append(Explosion(e.x, e.y))
                        global_kills += 1
                        if b.owner == "player":
                            player.kills += 1
                            player.score += 100
                        else:
                            ally.kills += 1
                        global_score += 100
                    break
            # check boss hit
            if b.alive and boss and boss.alive:
                if dist2(b.x, b.y, boss.x, boss.y) < Boss.RADIUS + b.radius:
                    boss.take_damage(b.damage)
                    b.alive = False
                    if not boss.alive:
                        # big explosion when boss dies
                        for _ in range(6):
                            ox = boss.x + random.uniform(-80, 80)
                            oy = boss.y + random.uniform(-80, 80)
                            explosions.append(Explosion(ox, oy, big=True))
                        global_kills += 1
                        if b.owner == "player":
                            player.kills += 1
                            player.score += 2000
                        global_score += 2000

        if b.owner == "enemy":
            if player.alive and dist2(b.x, b.y, player.x, player.y) < 25 + b.radius:
                player.take_damage(b.damage)
                b.alive = False
                if not player.alive:
                    explosions.append(Explosion(player.x, player.y))
            elif ally.alive and dist2(b.x, b.y, ally.x, ally.y) < Ally.RADIUS + b.radius:
                ally.take_damage(b.damage)
                b.alive = False
                if not ally.alive:
                    explosions.append(Explosion(ally.x, ally.y))

        for c in crates:
            if not c.alive:
                continue
            if dist2(b.x, b.y, c.x, c.y) < Crate.SZ + b.radius:
                b.alive = False
                if b.missile:
                    c.alive = False
                    explosions.append(Explosion(c.x, c.y))
                break

        for t in trees:
            if dist2(b.x, b.y, t.x, t.y) < Tree.BULLET_R + b.radius:
                b.alive = False
                break

        for bm in bombs:
            if not bm.alive or bm.triggered:
                continue
            if dist2(b.x, b.y, bm.x, bm.y) < Bomb.RADIUS + b.radius:
                bm.trigger()
                b.alive = False
                break

    tank_positions = []
    if player.alive:
        tank_positions.append((player.x, player.y))
    if ally.alive:
        tank_positions.append((ally.x, ally.y))
    for e in enemies:
        if e.alive:
            tank_positions.append((e.x, e.y))
    if boss and boss.alive:
        tank_positions.append((boss.x, boss.y))

    for bm in bombs:
        if not bm.alive or bm.triggered:
            continue
        for tx, ty in tank_positions:
            if dist2(tx, ty, bm.x, bm.y) < Bomb.STEP_R:
                bm.trigger()
                break

    for bm in bombs:
        if not bm.alive:
            bm.triggered = False
            explosions.append(Explosion(bm.x, bm.y, big=True))
            for who in [player, ally] + list(enemies):
                if not who.alive:
                    continue
                if dist2(bm.x, bm.y, who.x, who.y) < Bomb.EXPLODE_R:
                    who.take_damage(999)
            if boss and boss.alive:
                if dist2(bm.x, bm.y, boss.x, boss.y) < Bomb.EXPLODE_R * 1.5:
                    boss.take_damage(200)
            bm.x = bm.y = 99999

    # flag pickup logic
    if not flag.player_has:
        sx = flag.gx if not flag.gold_at_base else ENEMY_BASE[0]
        sy = flag.gy if not flag.gold_at_base else ENEMY_BASE[1]
        if dist2(sx, sy, player.x, player.y) < 48:
            flag.gold_at_base = False
            flag.player_has   = True
            player.has_flag   = True

    if player.has_flag:
        if dist2(PLAYER_BASE[0], PLAYER_BASE[1], player.x, player.y) < BASE_R:
            player.has_flag = False
            flag.player_has = False
            flag.reset()
            player.captures += 1
            player.score    += 500
            global_score    += 500

    for e in enemies:
        if not e.alive:
            continue
        if not flag.enemy_has and e.role == "flag_stealer":
            sx = flag.bx if not flag.blue_at_base else PLAYER_BASE[0]
            sy = flag.by if not flag.blue_at_base else PLAYER_BASE[1]
            if dist2(sx, sy, e.x, e.y) < 48:
                flag.blue_at_base = False
                flag.enemy_has    = True
                e.has_flag        = True
                flag.e_carrier    = e

    if flag.enemy_has and flag.e_carrier and flag.e_carrier.alive:
        ec = flag.e_carrier
        if dist2(ENEMY_BASE[0], ENEMY_BASE[1], ec.x, ec.y) < BASE_R:
            ec.has_flag    = False
            flag.enemy_has = False
            flag.e_carrier = None
            flag.reset()
            global_score = max(0, global_score - 200)

def check_round_complete():
    # returns True if all required waves for this round are cleared
    cfg = ROUND_CONFIG[current_round]
    return round_waves_cleared >= cfg["waves"]

def check_win_lose():
    global game_state, _result_recorded, upgrade_tokens, levelup_timer
    global current_round, round_waves_cleared, wave

    if not player.alive and game_state == S_PLAY:
        if not _result_recorded:
            _result_recorded = True
            record_game_result("OVER")
        game_state = S_OVER
        return

    if player.captures >= 3 and game_state == S_PLAY:
        if check_round_complete():
            if current_round >= MAX_ROUNDS:
                if not _result_recorded:
                    _result_recorded = True
                    record_game_result("CLEARED")
                game_state = S_GAMECLEAR
            else:
                # give upgrade tokens and go to level up screen
                upgrade_tokens += 2
                levelup_timer   = LEVELUP_HOLD
                game_state      = S_LEVELUP

def check_wave_win():
    # win condition for round 5: kill the boss
    global game_state, _result_recorded, upgrade_tokens, levelup_timer
    global current_round, round_waves_cleared

    if current_round == MAX_ROUNDS and boss and not boss.alive:
        if not _result_recorded:
            _result_recorded = True
            record_game_result("CLEARED")
        game_state = S_GAMECLEAR

def advance_to_next_round():
    global current_round, round_waves_cleared, wave, wave_active, wave_delay
    global bullets, enemies, explosions, boss
    current_round       += 1
    round_waves_cleared  = 0
    wave                 = 1
    wave_delay           = 0.0
    wave_active          = False
    bullets              = []
    enemies              = []
    explosions           = []
    boss                 = None
    flag.reset()
    # reset player position and partial hp restore
    player.x           = -500.0
    player.y           = -500.0
    player.has_flag    = False
    player.captures    = 0
    player.alive       = True
    player.hp          = min(player.max_hp, player.hp + player.max_hp // 3)
    player.reloading   = False
    player.shield_on   = False
    player.shield_cd   = 0.0
    player.missile_cd  = 0.0
    player.apply_upgrades()
    ally.__init__()
    generate_obstacles()
    start_wave(wave)


def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, WIN_W / WIN_H, 1.0, 5000.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    if first_person:
        eye_z      = 52.0
        rb         = math.radians(player.angle + player.turret_a)
        ex, ey, ez = player.x, player.y, eye_z
        pitch_down = 0.12
        look_dist  = 500.0
        lx = ex + math.cos(rb) * look_dist
        ly = ey + math.sin(rb) * look_dist
        lz = ez - math.sin(pitch_down) * look_dist
        gluLookAt(ex, ey, ez, lx, ly, lz, 0, 0, 1)
    else:
        rh = math.radians(cam_angle + player.angle)
        rv = math.radians(cam_pitch)
        cx = player.x - math.cos(rh) * math.cos(rv) * cam_dist
        cy = player.y - math.sin(rh) * math.cos(rv) * cam_dist
        cz = math.sin(rv) * cam_dist
        gluLookAt(cx, cy, cz, player.x, player.y, 22, 0, 0, 1)

def draw_tank(x, y, body_a, turret_a, col, hp_r=1.0, shield=False, carry_flag=False, big=False):
    scale = 1.6 if big else 1.0
    glPushMatrix()
    glTranslatef(x, y, 0)
    glRotatef(body_a, 0, 0, 1)

    glColor3f(*col)
    glPushMatrix()
    glTranslatef(0, 0, 18 * scale)
    glScalef(scale, scale * 0.85, scale * 0.45)
    glutSolidCube(44)
    glPopMatrix()

    glColor3f(0.14, 0.14, 0.14)
    for side in [22, -22]:
        glPushMatrix()
        glTranslatef(0, side * scale, 9 * scale)
        glScalef(1.55 * scale, 0.32 * scale, 0.32 * scale)
        glutSolidCube(44)
        glPopMatrix()

    glPushMatrix()
    glTranslatef(0, 0, 37 * scale)
    glColor3f(col[0]*0.75, col[1]*0.75, col[2]*0.75)
    gluCylinder(gluNewQuadric(), 15*scale, 12*scale, 11*scale, 10, 4)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(0, 0, 44 * scale)
    glRotatef(turret_a, 0, 0, 1)
    glColor3f(0.22, 0.22, 0.22)
    glRotatef(90, 0, 1, 0)
    gluCylinder(gluNewQuadric(), 4*scale, 3*scale, 46*scale, 8, 4)
    glPopMatrix()

    if shield:
        glColor3f(0.35, 0.75, 1.0)
        glPushMatrix()
        glTranslatef(0, 0, 22 * scale)
        gluSphere(gluNewQuadric(), 48 * scale, 10, 8)
        glPopMatrix()

    if carry_flag:
        glPushMatrix()
        glTranslatef(0, 0, 44 * scale)
        glColor3f(0.85, 0.85, 0.85)
        gluCylinder(gluNewQuadric(), 2, 2, 30, 6, 3)
        glTranslatef(0, 0, 30)
        glColor3f(1.0, 0.9, 0.0)
        glBegin(GL_QUADS)
        glVertex3f(0, 0, 0); glVertex3f(20, 7, 0)
        glVertex3f(20, 7, 10); glVertex3f(0, 0, 10)
        glEnd()
        glPopMatrix()

    # extra barrels for boss tank
    if big:
        glColor3f(col[0]*0.6, col[1]*0.6, col[2]*0.6)
        for vx, vy in [(-20, 0), (20, 0), (0, -20)]:
            glPushMatrix()
            glTranslatef(vx, vy, 55)
            gluCylinder(gluNewQuadric(), 4, 2, 18, 6, 2)
            glPopMatrix()

    # health bar
    bw = 52 * scale
    bh = 5
    glPushMatrix()
    glTranslatef(-bw/2, 0, (74 + (scale - 1) * 30))
    glRotatef(-body_a, 0, 0, 1)
    glColor3f(0.28, 0, 0)
    glBegin(GL_QUADS)
    glVertex3f(0, 0, 0); glVertex3f(bw, 0, 0)
    glVertex3f(bw, bh, 0); glVertex3f(0, bh, 0)
    glEnd()
    glColor3f(1 - hp_r, hp_r, 0)
    glBegin(GL_QUADS)
    glVertex3f(0, 0, 0); glVertex3f(bw*hp_r, 0, 0)
    glVertex3f(bw*hp_r, bh, 0); glVertex3f(0, bh, 0)
    glEnd()
    glPopMatrix()
    glPopMatrix()

def draw_tree(t):
    th = ARENAS[arena_sel]
    glPushMatrix()
    glTranslatef(t.x, t.y, 0)
    glColor3f(*th["trunk"])
    gluCylinder(gluNewQuadric(), Tree.TRUNK_R, Tree.TRUNK_R * 0.7, 55, 8, 4)
    glPushMatrix()
    glTranslatef(0, 0, 55)
    glColor3f(*th["leaves"])
    gluSphere(gluNewQuadric(), Tree.CANOPY_R, 10, 8)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0, 0, 82)
    glColor3f(th["leaves"][0]*0.85, th["leaves"][1]*0.85, th["leaves"][2]*0.85)
    gluSphere(gluNewQuadric(), Tree.CANOPY_R * 0.65, 8, 6)
    glPopMatrix()
    glPopMatrix()

def draw_flag_pole(x, y, col):
    glPushMatrix()
    glTranslatef(x, y, 0)
    glColor3f(0.65, 0.65, 0.65)
    gluCylinder(gluNewQuadric(), 2, 2, 64, 6, 4)
    glTranslatef(0, 0, 64)
    glColor3f(*col)
    glBegin(GL_QUADS)
    glVertex3f(0, 0, 0); glVertex3f(24, 9, 0)
    glVertex3f(24, 9, 14); glVertex3f(0, 0, 14)
    glEnd()
    glPopMatrix()

def draw_bullet(b):
    glPushMatrix()
    glTranslatef(b.x, b.y, 15)
    if b.missile:
        glColor3f(1.0, 0.45, 0.05)
    elif b.owner == "player":
        glColor3f(1.0, 1.0, 0.0)
    elif b.owner == "ally":
        glColor3f(0.30, 1.0, 0.50)
    else:
        glColor3f(1.0, 0.28, 0.08)
    gluSphere(gluNewQuadric(), b.radius, 8, 6)
    glPopMatrix()

def draw_explosion(e):
    prog = 1.0 - (e.timer / e.max)
    r    = (48 if e.big else 30) + prog * (120 if e.big else 62)
    a    = e.timer / e.max
    glPushMatrix()
    glTranslatef(e.x, e.y, 14)
    glColor3f(1.0, 0.5 * a, 0.0)
    gluSphere(gluNewQuadric(), r, 10, 8)
    glColor3f(1.0, 1.0, 0.25)
    gluSphere(gluNewQuadric(), r * 0.5, 8, 6)
    glPopMatrix()

def draw_arena():
    th   = ARENAS[arena_sel]
    tile = 120
    for tx in range(-ARENA, ARENA, tile):
        for ty in range(-ARENA, ARENA, tile):
            c = th["fa"] if ((tx // tile + ty // tile) % 2 == 0) else th["fb"]
            glColor3f(*c)
            glBegin(GL_QUADS)
            glVertex3f(tx,        ty,        0)
            glVertex3f(tx + tile, ty,        0)
            glVertex3f(tx + tile, ty + tile, 0)
            glVertex3f(tx,        ty + tile, 0)
            glEnd()

    glColor3f(*th["wall"])
    for wx, wy, ww, wh in [
        (-ARENA,          -ARENA,        ARENA*2, WALL_T),
        (-ARENA,           ARENA-WALL_T, ARENA*2, WALL_T),
        (-ARENA,          -ARENA,        WALL_T,  ARENA*2),
        ( ARENA - WALL_T, -ARENA,        WALL_T,  ARENA*2),
    ]:
        glPushMatrix()
        glTranslatef(wx + ww/2, wy + wh/2, 22)
        glScalef(ww, wh, 44)
        glutSolidCube(1)
        glPopMatrix()

    for bx, by, bc in [
        (PLAYER_BASE[0], PLAYER_BASE[1], (0.10, 0.50, 1.00)),
        (ENEMY_BASE[0],  ENEMY_BASE[1],  (1.00, 0.20, 0.20)),
    ]:
        glPushMatrix()
        glTranslatef(bx, by, 0)
        glColor3f(*bc)
        gluCylinder(gluNewQuadric(), BASE_R, BASE_R, 6, 24, 2)
        glPopMatrix()

    for t in trees:
        draw_tree(t)

    if flag.gold_at_base:
        draw_flag_pole(ENEMY_BASE[0], ENEMY_BASE[1], (1.0, 0.9, 0.0))
    elif not flag.player_has:
        draw_flag_pole(flag.gx, flag.gy, (1.0, 0.9, 0.0))

    if flag.blue_at_base:
        draw_flag_pole(PLAYER_BASE[0], PLAYER_BASE[1], (0.30, 0.55, 1.0))
    elif not flag.enemy_has:
        draw_flag_pole(flag.bx, flag.by, (0.30, 0.55, 1.0))

    crate_colors = [
        (0.68, 0.52, 0.32),
        (0.52, 0.72, 0.88),
        (0.42, 0.24, 0.12),
        (0.35, 0.55, 0.25),
    ]
    cc = crate_colors[arena_sel]
    for c in crates:
        if not c.alive:
            continue
        glPushMatrix()
        glTranslatef(c.x, c.y, Crate.SZ / 2)
        glColor3f(*cc)
        glutSolidCube(Crate.SZ)
        glColor3f(cc[0]*0.55, cc[1]*0.55, cc[2]*0.55)
        hs = Crate.SZ / 2
        glBegin(GL_LINES)
        glVertex3f(-hs, 0, hs + 0.5); glVertex3f(hs, 0, hs + 0.5)
        glVertex3f(0, -hs, hs + 0.5); glVertex3f(0,  hs, hs + 0.5)
        glEnd()
        glPopMatrix()

    t_ms = glutGet(GLUT_ELAPSED_TIME)
    for bm in bombs:
        if not bm.alive or bm.x > 9000:
            continue
        pulse = abs(math.sin(t_ms / 260.0))
        if bm.triggered:
            glColor3f(0.9, 0.1 + pulse*0.6, 0.05)
        else:
            glColor3f(0.12, 0.12, 0.12)
        glPushMatrix()
        glTranslatef(bm.x, bm.y, Bomb.RADIUS)
        gluSphere(gluNewQuadric(), Bomb.RADIUS, 12, 10)
        glColor3f(0.9, 0.7, 0.1)
        glPushMatrix()
        glTranslatef(0, 0, Bomb.RADIUS)
        glRotatef(30, 1, 0, 0)
        gluCylinder(gluNewQuadric(), 1.5, 1.5, 15, 5, 3)
        glPopMatrix()
        glPopMatrix()

def auto_aim_fire():
    al = [e for e in enemies if e.alive]
    if boss and boss.alive:
        al.append(boss)
    if not al:
        return
    nearest = min(al, key=lambda e: dist2(player.x, player.y, e.x, e.y))
    dx = nearest.x - player.x
    dy = nearest.y - player.y
    player.turret_a = math.degrees(math.atan2(dy, dx)) - player.angle
    b = player.fire()
    if b:
        bullets.append(b)

def draw_hud():
    draw_rect2d(5, 5, 230, 178, (0.04, 0.04, 0.09))
    draw_text_big(14, 160, "YOU", color=(0.30, 1.0, 0.50))
    hp_r = max(0, player.hp / player.max_hp)
    draw_rect2d(14, 138, 208, 14, (0.24, 0, 0))
    draw_rect2d(14, 138, 208 * hp_r, 14, (1 - hp_r, hp_r, 0))
    draw_text(14, 123, f"HP {player.hp}/{player.max_hp}")
    atxt = "RELOADING..." if player.reloading else f"Ammo {player.ammo}/{player.max_ammo}"
    draw_text(14, 103, atxt, color=(1.0, 0.9, 0.3))
    t = TANK_TYPES[player.tank_type]
    draw_text(14, 83, f"Tank: {t['label']}", color=t["col"])
    if player.shield_on:
        draw_text(14, 63, f"SHIELD {player.shield_t:.1f}s", color=(0.40, 0.80, 1.0))
    elif player.shield_cd > 0:
        draw_text(14, 63, f"Shield CD {player.shield_cd:.1f}s", color=(0.35, 0.35, 0.55))
    else:
        draw_text(14, 63, "Shield READY [F]", color=(0.30, 0.75, 1.0))
    if player.missile_cd > 0:
        draw_text(14, 43, f"Missile CD {player.missile_cd:.1f}s", color=(0.50, 0.40, 0.20))
    else:
        draw_text(14, 43, "Missile READY [G]", color=(1.0, 0.60, 0.10))
    draw_text(14, 20, f"Score {player.score}  Kills {player.kills}", color=(0.8, 0.8, 0.5))

    # round progress bar at top
    cfg     = ROUND_CONFIG[current_round]
    r_col   = cfg["color"]
    draw_rect2d(WIN_W//2 - 240, WIN_H - 34, 480, 28, (0.05, 0.05, 0.05))
    for ri in range(1, MAX_ROUNDS + 1):
        px = WIN_W//2 - 200 + (ri - 1) * 72
        if ri < current_round:
            col = (0.2, 0.8, 0.2)
        elif ri == current_round:
            col = r_col
        else:
            col = (0.2, 0.2, 0.2)
        draw_rect2d(px, WIN_H - 30, 60, 20, col)
        lbl = "BOSS" if ri == MAX_ROUNDS else f"R{ri}"
        draw_text(px + 4, WIN_H - 22, lbl,
                  GLUT_BITMAP_HELVETICA_12,
                  (0, 0, 0) if ri == current_round else (0.6, 0.6, 0.6))

    # boss health bar
    if boss and boss.alive:
        bw = 500
        bx = WIN_W//2 - bw//2
        by = WIN_H - 70
        pulse = abs(math.sin(glutGet(GLUT_ELAPSED_TIME) / 300.0))
        phase_col = (1.0, 0.2 + 0.4*pulse, 0.0) if boss.phase == 2 else (0.85, 0.1, 0.1)
        draw_rect2d(bx, by, bw, 18, (0.3, 0, 0))
        draw_rect2d(bx, by, int(bw * boss.hp_ratio), 18, phase_col)
        phase_lbl = "  !! ENRAGED !!" if boss.phase == 2 else ""
        draw_text_big(bx, by + 22,
                      f"BOSS — {boss.hp}/{boss.max_hp}{phase_lbl}",
                      color=(1.0, 0.3, 0.1) if boss.phase == 2 else (1.0, 0.6, 0.1))

    # enemy leader panel
    al = [e for e in enemies if e.alive]
    draw_rect2d(WIN_W - 238, 5, 232, 178, (0.09, 0.04, 0.04))
    draw_text_big(WIN_W - 234, 160, "ENEMY LEADER", color=(1.0, 0.35, 0.35))
    if al:
        ld = max(al, key=lambda e: e.score + e.kills * 50)
        lr = max(0, ld.hp / ld.max_hp)
        draw_rect2d(WIN_W - 234, 138, 216, 14, (0.24, 0, 0))
        draw_rect2d(WIN_W - 234, 138, 216 * lr, 14, (1 - lr, lr, 0))
        draw_text(WIN_W - 234, 123, f"HP {ld.hp}/{ld.max_hp}")
        draw_text(WIN_W - 234, 103, f"Role: {ld.role.replace('_',' ').title()}", color=(0.9, 0.6, 0.6))
        draw_text(WIN_W - 234, 83,  f"Score {ld.score}  Kills {ld.kills}", color=(0.8, 0.6, 0.5))
        draw_text(WIN_W - 234, 63,  f"Alive: {len(al)}", color=(1.0, 0.5, 0.5))
        if flag.enemy_has:
            draw_text(WIN_W - 234, 43, "STEALING YOUR FLAG!", color=(1.0, 0.25, 0.05))
    else:
        if boss and boss.alive:
            draw_text(WIN_W - 234, 90, "BOSS ACTIVE!", color=(1.0, 0.3, 0.1))
        else:
            draw_text(WIN_W - 234, 90, "All enemies dead", color=(0.5, 0.85, 0.5))

    # ally panel
    draw_rect2d(5, WIN_H - 88, 210, 82, (0.03, 0.06, 0.03))
    draw_text_big(14, WIN_H - 22, "ALLY TANK", color=(0.40, 1.0, 0.50))
    if ally.alive:
        ar = max(0, ally.hp / ally.max_hp)
        draw_rect2d(14, WIN_H - 42, 190, 12, (0.20, 0, 0))
        draw_rect2d(14, WIN_H - 42, 190 * ar, 12, (1 - ar, ar, 0))
        draw_text(14, WIN_H - 60, f"HP {ally.hp}/{ally.max_hp}  Kills {ally.kills}", color=(0.7, 0.9, 0.7))
        draw_text(14, WIN_H - 78, "Targeting nearest enemy", color=(0.5, 0.7, 0.5))
    else:
        draw_text(14, WIN_H - 52, "DESTROYED", color=(0.8, 0.2, 0.2))

    draw_text(WIN_W//2 - 120, WIN_H - 54,
              f"WAVE {wave}/{ROUND_CONFIG[current_round]['waves']}   "
              f"GLOBAL {global_score}   ARENA: {ARENAS[arena_sel]['name']}",
              color=(1.0, 0.80, 0.20))
    draw_text(WIN_W//2 - 70, WIN_H - 74, f"Captures {player.captures}/3", color=(0.9, 0.9, 0.4))

    elapsed = int((glutGet(GLUT_ELAPSED_TIME) / 1000.0) - _session_start_t)
    hs = get_high_score()
    draw_text(WIN_W//2 - 70, WIN_H - 96,
              f"Time {fmt_time(elapsed)}   Hi-Score {hs}",
              color=(0.55, 0.85, 0.95))

    if not wave_active and wave_delay > 0:
        is_boss_wave = (current_round == MAX_ROUNDS and wave == 3)
        lbl = "BOSS INCOMING" if is_boss_wave else f"WAVE {wave} INCOMING"
        col = (1.0, 0.2, 0.05) if is_boss_wave else (1.0, 0.6, 0.15)
        draw_text_big(WIN_W//2 - 140, WIN_H//2 - 10,
                      f"{lbl} in {int(wave_delay)+1}s", color=col)
    if player.has_flag:
        draw_rect2d(WIN_W//2 - 195, WIN_H//2 + 62, 390, 30, (0.14, 0.11, 0.0))
        draw_text_big(WIN_W//2 - 190, WIN_H//2 + 66,
                      "ENEMY FLAG! RETURN TO YOUR BASE", color=(1.0, 0.9, 0.0))
    if flag.enemy_has:
        draw_rect2d(WIN_W//2 - 190, WIN_H//2 + 26, 380, 30, (0.14, 0.0, 0.0))
        draw_text_big(WIN_W//2 - 185, WIN_H//2 + 30,
                      "YOUR FLAG IS BEING STOLEN!", color=(1.0, 0.28, 0.05))
    if player.cheat_aim:
        draw_text(WIN_W//2 - 58, WIN_H - 116, "AUTO-AIM ON", color=(1.0, 0.30, 1.0))

    cam_mode = "1st Person" if first_person else "3rd Person"
    draw_text(WIN_W - 168, WIN_H - 26, cam_mode, color=(0.5, 0.5, 0.5))
    draw_minimap()

def draw_minimap():
    MM = 130
    ox = WIN_W - MM - 8
    oy = 8
    sc = MM / (ARENA * 2)
    draw_rect2d(ox, oy, MM, MM, (0.04, 0.08, 0.04))
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    def pt(wx, wy, col, sz=5):
        px = ox + (wx + ARENA) * sc
        py = oy + (wy + ARENA) * sc
        glColor3f(*col)
        glPointSize(sz)
        glBegin(GL_POINTS)
        glVertex2f(px, py)
        glEnd()

    pt(*PLAYER_BASE, (0.20, 0.50, 1.00), 10)
    pt(*ENEMY_BASE,  (1.00, 0.20, 0.20), 10)
    for t in trees:
        pt(t.x, t.y, (0.20, 0.55, 0.15), 4)
    if player.alive:
        pt(player.x, player.y, (0.00, 1.00, 0.00), 8)
    if ally.alive:
        pt(ally.x, ally.y, (0.30, 1.00, 0.55), 7)
    for e in enemies:
        if e.alive:
            pt(e.x, e.y, (1.0, 0.3, 0.0), 5)
    if boss and boss.alive:
        t_ms = glutGet(GLUT_ELAPSED_TIME)
        pulse = abs(math.sin(t_ms / 200.0))
        pt(boss.x, boss.y, (1.0, 0.1, 0.1 + 0.5 * pulse), 12)
    if not flag.gold_at_base and not flag.player_has:
        pt(flag.gx, flag.gy, (1.0, 0.9, 0.0), 6)
    if not flag.blue_at_base and not flag.enemy_has:
        pt(flag.bx, flag.by, (0.3, 0.5, 1.0), 6)
    for bm in bombs:
        if bm.alive and bm.x < 9000:
            pt(bm.x, bm.y, (0.8, 0.1, 0.1), 4)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_menu():
    draw_rect2d(0, 0, WIN_W, WIN_H, (0.04, 0.04, 0.08))
    draw_text_big(WIN_W//2 - 230, WIN_H - 90,
                  "SIEGE TANKS: ARENA DOMINATION  v5", color=(1.0, 0.70, 0.0))
    draw_text(WIN_W//2 - 190, WIN_H - 120,
              "5 ROUNDS  |  UPGRADES  |  BOSS BATTLE", color=(0.70, 0.55, 0.20))

    hs = get_high_score()
    if hs > 0:
        draw_rect2d(WIN_W//2 - 160, WIN_H - 158, 320, 28, (0.10, 0.10, 0.04))
        draw_text(WIN_W//2 - 155, WIN_H - 148,
                  f"ALL-TIME HIGH SCORE:  {hs}", color=(1.0, 0.90, 0.10))

    options = ["  > PLAY", "  > SCORES", "  > INSTRUCTIONS", "  > EXIT"]
    colors  = [(0.2, 1.0, 0.4), (0.20, 0.85, 1.0), (0.3, 0.8, 1.0), (1.0, 0.3, 0.3)]
    for i, (o, c) in enumerate(zip(options, colors)):
        col = c if i == menu_sel else (0.38, 0.38, 0.38)
        draw_text_big(WIN_W//2 - 145, WIN_H//2 + 80 - i*55, o, color=col)
    draw_text(WIN_W//2 - 145, 38, "UP/DOWN to navigate, ENTER to select", color=(0.4, 0.4, 0.4))

def draw_arena_select():
    draw_rect2d(0, 0, WIN_W, WIN_H, (0.04, 0.06, 0.04))
    draw_text_big(WIN_W//2 - 110, WIN_H - 68, "SELECT ARENA", color=(0.8, 1.0, 0.4))
    for i, a in enumerate(ARENAS):
        col = (1.0, 0.9, 0.2) if i == arena_sel else (0.45, 0.45, 0.45)
        pre = "[*] " if i == arena_sel else "[ ] "
        draw_text_big(WIN_W//2 - 135, WIN_H//2 + 85 - i*60, pre + a["name"], color=col)
    draw_text(WIN_W//2 - 135, 40,
              "LEFT/RIGHT or UP/DOWN to choose, ENTER to confirm", color=(0.40, 0.40, 0.40))

def draw_levelup_screen():
    # shown between rounds for upgrade selection
    cfg      = ROUND_CONFIG[min(current_round + 1, MAX_ROUNDS)]
    next_lbl = cfg["label"]
    next_col = cfg["color"]

    draw_rect2d(0, 0, WIN_W, WIN_H, (0.02, 0.06, 0.02))
    draw_rect2d(WIN_W//2 - 300, WIN_H - 70, 600, 50, (0.05, 0.18, 0.05))
    draw_text_big(WIN_W//2 - 185, WIN_H - 38,
                  f"ROUND {current_round} COMPLETE!", color=(0.3, 1.0, 0.3))

    # round progress indicators
    for ri in range(1, MAX_ROUNDS + 1):
        px = WIN_W//2 - 235 + (ri - 1) * 95
        if ri <= current_round:
            col = (0.2, 0.9, 0.2)
        else:
            col = (0.1, 0.2, 0.1)
        draw_rect2d(px, WIN_H - 92, 82, 14, col)
        lbl = "BOSS" if ri == MAX_ROUNDS else f"R{ri}"
        draw_text(px + 6, WIN_H - 84, lbl,
                  GLUT_BITMAP_HELVETICA_12,
                  (0, 0, 0) if ri <= current_round else (0.4, 0.4, 0.4))

    draw_text_big(WIN_W//2 - 180, WIN_H - 118,
                  f"NEXT: {next_lbl}", color=next_col)

    # stats summary
    draw_rect2d(WIN_W//2 - 220, WIN_H - 190, 440, 60, (0.03, 0.07, 0.03))
    draw_text(WIN_W//2 - 210, WIN_H - 148,
              f"Score: {global_score}    Kills: {global_kills}    Captures: {player.captures}",
              color=(0.85, 0.85, 0.4))
    draw_text(WIN_W//2 - 210, WIN_H - 168,
              f"Your HP: {player.hp}/{player.max_hp}    Tokens to spend: {upgrade_tokens}",
              color=(0.4, 0.9, 0.9))

    draw_text_big(WIN_W//2 - 260, WIN_H - 218,
                  "CHOOSE AN UPGRADE  (ENTER = buy, ESC = skip all)", color=(1.0, 0.9, 0.2))
    for i, up in enumerate(UPGRADES):
        is_sel = (i == upgrade_menu_sel)
        by2    = WIN_H - 258 - i * 48
        bg_col = (0.08, 0.18, 0.08) if is_sel else (0.04, 0.08, 0.04)
        draw_rect2d(WIN_W//2 - 260, by2 - 4, 520, 42, bg_col)
        if is_sel:
            draw_rect2d(WIN_W//2 - 264, by2 - 8, 528, 50, (0.15, 0.45, 0.15))
            draw_rect2d(WIN_W//2 - 260, by2 - 4, 520, 42, bg_col)
        cur_val = player_upgrades[up["id"]]
        can_buy = upgrade_tokens >= up["cost"]
        col = (0.3, 1.0, 0.3) if (is_sel and can_buy) else \
              (0.6, 0.6, 0.6) if not can_buy else (0.7, 0.85, 0.7)
        draw_text_big(WIN_W//2 - 248, by2 + 16,
                      f"{up['label']}  [x{cur_val}]", color=col)
        if is_sel and not can_buy:
            draw_text(WIN_W//2 + 100, by2 + 16, "NOT ENOUGH TOKENS", color=(0.8, 0.2, 0.2))

    draw_text(WIN_W//2 - 200, 48,
              "ENTER = Buy upgrade    ESC = Continue to next round",
              color=(0.5, 0.7, 0.5))
    draw_text(WIN_W - 200, 28,
              f"Auto-continue in {int(levelup_timer) + 1}s",
              color=(0.35, 0.35, 0.35))

def draw_gameclear_screen():
    elapsed = int((glutGet(GLUT_ELAPSED_TIME) / 1000.0) - _session_start_t)
    hs = get_high_score()
    is_new_hs = (global_score >= hs and global_score > 0)

    t_ms = glutGet(GLUT_ELAPSED_TIME)
    pulse = abs(math.sin(t_ms / 350.0))

    draw_rect2d(0, 0, WIN_W, WIN_H, (0.0, 0.05, 0.15))
    draw_rect2d(WIN_W//2 - 340, WIN_H - 90, 680, 60,
                (0.04 + 0.04*pulse, 0.08, 0.22 + 0.06*pulse))
    draw_text_big(WIN_W//2 - 320, WIN_H - 52,
                  "CAMPAIGN CLEARED — ALL 5 ROUNDS DEFEATED!", color=(0.3, 0.9, 1.0))
    draw_text_big(WIN_W//2 - 180, WIN_H - 106,
                  "THE BOSS HAS FALLEN. VICTORY IS YOURS.", color=(1.0, 0.85, 0.2))

    if is_new_hs:
        draw_rect2d(WIN_W//2 - 180, WIN_H - 150, 360, 30, (0.06, 0.06, 0.22))
        draw_text_big(WIN_W//2 - 170, WIN_H - 134, "★  NEW HIGH SCORE!  ★", color=(1.0, 0.95, 0.0))

    draw_rect2d(WIN_W//2 - 250, WIN_H - 220, 500, 56, (0.03, 0.06, 0.12))
    draw_text_big(WIN_W//2 - 160, WIN_H - 178,
                  f"Final Score:  {global_score}", color=(1.0, 0.80, 0.20))
    draw_text(WIN_W//2 - 200, WIN_H - 210,
              f"Kills: {global_kills}   Captures: {player.captures}   "
              f"Time: {fmt_time(elapsed)}", color=(0.85, 0.85, 0.85))
    draw_text(WIN_W//2 - 200, WIN_H - 246,
              f"All-Time High Score: {hs}", color=(1.0, 0.90, 0.10))

    for ri in range(1, MAX_ROUNDS + 1):
        px = WIN_W//2 - 240 + (ri - 1) * 100
        col = (1.0, 0.85, 0.0) if ri == MAX_ROUNDS else (0.2, 0.9, 0.2)
        draw_rect2d(px, WIN_H - 278, 88, 22, col)
        lbl = "BOSS ✓" if ri == MAX_ROUNDS else f"R{ri} ✓"
        draw_text(px + 4, WIN_H - 262, lbl, GLUT_BITMAP_HELVETICA_12, (0, 0, 0))

    draw_rect2d(WIN_W//2 - 260, WIN_H - 290, 520, 2, (0.2, 0.4, 0.6))

    records = _load_scores()
    if records:
        draw_text(WIN_W//2 - 200, WIN_H - 310, "TOP SCORES:", color=(0.45, 0.75, 0.85))
        for rank, r in enumerate(records[:4]):
            tag = "CLEARED" if r.get("result") == "CLEARED" else r.get("result","?")
            draw_text(WIN_W//2 - 200, WIN_H - 336 - rank * 22,
                      f"  #{rank+1}  {r['score']:>6}  {tag:<7}  {r['arena']:<8}  "
                      f"R{r.get('round',1)}  {fmt_time(r['playtime_s'])}  {r['date']}",
                      color=(0.40, 0.70, 0.80))

    draw_text(WIN_W//2 - 200, 44, "R = Play Again       ESC = Main Menu", color=(0.6, 0.6, 0.5))

def draw_instructions():
    draw_rect2d(0, 0, WIN_W, WIN_H, (0.04, 0.05, 0.04))
    draw_text_big(WIN_W//2 - 112, WIN_H - 58, "INSTRUCTIONS", color=(1.0, 0.9, 0.2))
    lines = [
        "W / S            Move forward / backward",
        "A / D            Rotate tank body",
        "Left Click       Fire normal bullet",
        "R                Reload ammo",
        "F                Activate SHIELD  (75% dmg reduction, 5s, CD 15s)",
        "G                Fire MISSILE  (4x AOE damage, CD 8s)",
        "Arrow Keys       Orbit / tilt camera (3rd person)",
        "Right Click      Toggle 1st / 3rd person camera",
        "C    CHEAT       Switch tank type: Light > Balanced > Heavy",
        "V    CHEAT       Toggle auto-aim + auto-fire",
        "ESC              Pause / return to menu",
        "",
        "5-ROUND CAMPAIGN:",
        "  Round 1-4: Capture 3 flags to complete the round.",
        "  Each round is harder — more enemies, more HP, more damage.",
        "  After each round you earn 2 UPGRADE TOKENS.",
        "  Round 5 is the BOSS BATTLE — defeat the Boss Tank to win!",
        "",
        "UPGRADES (level-up screen between rounds):",
        "  +HP, +Ammo, Shield CD reduction, Missile CD reduction,",
        "  Speed boost, Damage boost.  Each costs 1 token.",
        "",
        "BOSS (Round 5):",
        "  Phase 1: Heavy fire, charges health.  Phase 2 at 50% HP:",
        "  Enraged — triple-shot burst, faster movement, circle-strafe.",
        "  Defeat all enemies in waves 1-2 first, then face the boss.",
        "",
        "ESC to go back",
    ]
    for i, l in enumerate(lines):
        col = (1.0, 0.6, 0.1) if l.startswith(("5-ROUND", "UPGRADES", "BOSS ")) else (0.88, 0.88, 0.88)
        draw_text(85, WIN_H - 108 - i*23, l, color=col)

def draw_gameover():
    elapsed = int((glutGet(GLUT_ELAPSED_TIME) / 1000.0) - _session_start_t)
    hs = get_high_score()
    is_new_hs = (global_score >= hs and global_score > 0)

    draw_rect2d(0, 0, WIN_W, WIN_H, (0.14, 0.0, 0.0))
    draw_text_big(WIN_W//2 - 115, WIN_H//2 + 120, "GAME  OVER", color=(1.0, 0.2, 0.2))
    draw_text(WIN_W//2 - 115, WIN_H//2 + 90,
              f"Fell on Round {current_round} / {MAX_ROUNDS}", color=(0.7, 0.3, 0.3))

    if is_new_hs:
        draw_rect2d(WIN_W//2 - 170, WIN_H//2 + 62, 340, 28, (0.18, 0.14, 0.0))
        draw_text_big(WIN_W//2 - 165, WIN_H//2 + 66, "★  NEW HIGH SCORE!  ★", color=(1.0, 0.95, 0.0))

    draw_text_big(WIN_W//2 - 135, WIN_H//2 + 32, f"Score: {global_score}", color=(1.0, 0.80, 0.20))
    draw_text(WIN_W//2 - 135, WIN_H//2 + 4,
              f"Kills: {global_kills}     Captures: {player.captures}     Waves: {wave}")
    draw_text(WIN_W//2 - 135, WIN_H//2 - 22, f"Time Played: {fmt_time(elapsed)}", color=(0.55, 0.85, 0.95))
    draw_text(WIN_W//2 - 135, WIN_H//2 - 48, f"All-Time High Score: {hs}", color=(1.0, 0.90, 0.10))

    draw_rect2d(WIN_W//2 - 220, WIN_H//2 - 56, 440, 2, (0.4, 0.1, 0.1))

    records = _load_scores()
    if records:
        draw_text(WIN_W//2 - 135, WIN_H//2 - 72, "TOP SCORES:", color=(0.85, 0.55, 0.55))
        for rank, r in enumerate(records[:3]):
            draw_text(WIN_W//2 - 135, WIN_H//2 - 94 - rank*20,
                      f"  #{rank+1}  {r['score']:>6}  {r.get('result','?')}  {r['arena']}  "
                      f"R{r.get('round',1)}  {fmt_time(r['playtime_s'])}  {r['date']}",
                      color=(0.80, 0.50, 0.50))

    draw_text(WIN_W//2 - 135, 52,
              "R = Restart          ESC = Main Menu          H = View Full Scores",
              color=(0.7, 0.7, 0.5))

def draw_scores_screen():
    draw_rect2d(0, 0, WIN_W, WIN_H, (0.03, 0.03, 0.10))
    draw_text_big(WIN_W//2 - 135, WIN_H - 55, "LEADERBOARD  —  TOP SCORES", color=(1.0, 0.85, 0.10))

    records = _load_scores()

    hx = 55
    draw_rect2d(hx - 4, WIN_H - 90, WIN_W - hx*2 + 8, 2, (0.4, 0.4, 0.1))
    draw_text(hx, WIN_H - 104,
              f"{'#':<3}  {'SCORE':>6}  {'RES':<8}  {'ARENA':<8}  {'RND':>3}  "
              f"{'KILLS':>5}  {'CAP':>3}  {'WAVES':>5}  {'TIME':>6}  DATE",
              color=(0.80, 0.80, 0.30))
    draw_rect2d(hx - 4, WIN_H - 112, WIN_W - hx*2 + 8, 2, (0.4, 0.4, 0.1))

    if not records:
        draw_text_big(WIN_W//2 - 140, WIN_H//2, "No scores yet — play a game!", color=(0.5, 0.5, 0.5))
    else:
        for rank, r in enumerate(records):
            if rank == 0:
                col = (1.00, 0.88, 0.15)
            elif rank == 1:
                col = (0.80, 0.80, 0.80)
            elif rank == 2:
                col = (0.80, 0.55, 0.25)
            else:
                col = (0.65, 0.65, 0.65)

            result_lbl = r.get("result", "?")[:7]
            row = (f"#{rank+1:<2}  {r['score']:>6}  {result_lbl:<8}  "
                   f"{r['arena']:<8}  R{r.get('round',1):>2}  {r['kills']:>5}  "
                   f"{r['captures']:>3}  {r['waves']:>5}  "
                   f"{fmt_time(r['playtime_s']):>6}  {r['date']}")
            draw_text(hx, WIN_H - 140 - rank * 26, row, color=col)

    draw_rect2d(hx - 4, 66, WIN_W - hx*2 + 8, 2, (0.3, 0.3, 0.1))
    draw_text(hx, 46, "ESC = Back to Menu", color=(0.45, 0.45, 0.45))

def draw_paused():
    draw_rect2d(WIN_W//2 - 190, WIN_H//2 - 50, 380, 100, (0.05, 0.05, 0.09))
    draw_text_big(WIN_W//2 - 66, WIN_H//2 + 22, "PAUSED", color=(1.0, 1.0, 0.3))
    draw_text(WIN_W//2 - 120, WIN_H//2 - 24,
              "ESC = Resume          Q = Quit to Menu", color=(0.7, 0.7, 0.7))

def reset_game():
    global bullets, enemies, explosions, global_score, global_kills
    global wave, wave_delay, wave_active
    global _session_start_t, _result_recorded
    global current_round, round_waves_cleared, upgrade_tokens, player_upgrades, boss
    player.reset()
    player._speed_bonus = 0.0
    player._dmg_bonus   = 0
    ally.__init__()
    flag.reset()
    bullets             = []
    enemies             = []
    explosions          = []
    boss                = None
    global_score        = 0
    global_kills        = 0
    wave                = 1
    wave_delay          = 0.0
    wave_active         = False
    current_round       = 1
    round_waves_cleared = 0
    upgrade_tokens      = 0
    player_upgrades     = {"hp": 0, "ammo": 0, "shield": 0, "missile": 0, "speed": 0, "dmg": 0}
    _session_start_t    = glutGet(GLUT_ELAPSED_TIME) / 1000.0
    _result_recorded    = False
    generate_obstacles()
    start_wave(wave)

auto_aim_acc = 0.0

def keyboardListener(key, x, y):
    global game_state, menu_sel, arena_sel, auto_aim_acc
    global upgrade_menu_sel, upgrade_tokens, player_upgrades

    if game_state == S_MENU:
        if key == b'\r':
            if menu_sel == 0:
                game_state = S_ARENA
            elif menu_sel == 1:
                game_state = S_SCORES
            elif menu_sel == 2:
                game_state = S_INSTR
            elif menu_sel == 3:
                glutLeaveMainLoop()
        if key == b'\x1b':
            glutLeaveMainLoop()
        return

    if game_state == S_ARENA:
        if key == b'\r':
            reset_game()
            game_state = S_PLAY
        if key == b'\x1b':
            game_state = S_MENU
        return

    if game_state == S_INSTR:
        if key == b'\x1b':
            game_state = S_MENU
        return

    if game_state == S_SCORES:
        if key == b'\x1b':
            game_state = S_MENU
        return

    if game_state == S_LEVELUP:
        if key == b'\r':
            up = UPGRADES[upgrade_menu_sel]
            if upgrade_tokens >= up["cost"]:
                upgrade_tokens -= up["cost"]
                player_upgrades[up["id"]] += 1
                player.apply_upgrades()
        if key == b'\x1b':
            advance_to_next_round()
            game_state = S_PLAY
        return

    if game_state in (S_OVER, S_WIN):
        if key in (b'r', b'R'):
            reset_game()
            game_state = S_PLAY
        if key in (b'h', b'H'):
            game_state = S_SCORES
        if key == b'\x1b':
            game_state = S_MENU
        return

    if game_state == S_GAMECLEAR:
        if key in (b'r', b'R'):
            reset_game()
            game_state = S_PLAY
        if key == b'\x1b':
            game_state = S_MENU
        return

    if game_state == S_PAUSE:
        if key == b'\x1b':
            game_state = S_PLAY
        if key in (b'q', b'Q'):
            game_state = S_MENU
        return

    if game_state == S_PLAY:
        if key == b'\x1b':
            game_state = S_PAUSE
            return
        if key in (b'w', b'W'):
            player.move_dir = 1
        if key in (b's', b'S'):
            player.move_dir = -1
        if key in (b'a', b'A'):
            player.rot_dir = 1
        if key in (b'd', b'D'):
            player.rot_dir = -1
        if key in (b'r', b'R'):
            player.reload()
        if key in (b'f', b'F'):
            player.shield()
        if key in (b'g', b'G'):
            m = player.fire_missile()
            if m:
                bullets.append(m)
        if key in (b'c', b'C'):
            player.switch_type()
        if key in (b'v', b'V'):
            player.cheat_aim = not player.cheat_aim
            auto_aim_acc     = 0.0

def keyboardUpListener(key, x, y):
    if game_state != S_PLAY:
        return
    if key in (b'w', b'W', b's', b'S'):
        player.move_dir = 0
    if key in (b'a', b'A', b'd', b'D'):
        player.rot_dir = 0

def specialKeyListener(key, x, y):
    global cam_angle, cam_pitch, menu_sel, arena_sel, upgrade_menu_sel
    if game_state == S_MENU:
        if key == GLUT_KEY_UP:
            menu_sel = (menu_sel - 1) % 4
        if key == GLUT_KEY_DOWN:
            menu_sel = (menu_sel + 1) % 4
        return
    if game_state == S_ARENA:
        if key in (GLUT_KEY_LEFT, GLUT_KEY_UP):
            arena_sel = (arena_sel - 1) % 4
        if key in (GLUT_KEY_RIGHT, GLUT_KEY_DOWN):
            arena_sel = (arena_sel + 1) % 4
        return
    if game_state == S_LEVELUP:
        if key == GLUT_KEY_UP:
            upgrade_menu_sel = (upgrade_menu_sel - 1) % len(UPGRADES)
        if key == GLUT_KEY_DOWN:
            upgrade_menu_sel = (upgrade_menu_sel + 1) % len(UPGRADES)
        return
    if game_state == S_PLAY:
        if key == GLUT_KEY_LEFT:
            cam_angle -= 5
        if key == GLUT_KEY_RIGHT:
            cam_angle += 5
        if key == GLUT_KEY_UP:
            cam_pitch = clamp(cam_pitch + 3, 10, 80)
        if key == GLUT_KEY_DOWN:
            cam_pitch = clamp(cam_pitch - 3, 10, 80)

def mouseListener(button, state, x, y):
    global first_person
    if game_state != S_PLAY:
        return
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        if not player.cheat_aim:
            b = player.fire()
            if b:
                bullets.append(b)
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        first_person = not first_person
        if first_person:
            glutSetCursor(GLUT_CURSOR_NONE)
            glutWarpPointer(WIN_W // 2, WIN_H // 2)
        else:
            glutSetCursor(GLUT_CURSOR_LEFT_ARROW)

def passiveMotionListener(mx, my):
    if game_state != S_PLAY:
        return
    cx = WIN_W // 2
    cy = WIN_H // 2
    dx = mx - cx
    dy = my - cy
    if first_person:
        if abs(dx) > 2 or abs(dy) > 2:
            player.turret_a += dx * 0.3
            glutWarpPointer(cx, cy)
    else:
        if abs(dx) > 5 or abs(dy) > 5:
            player.turret_a = math.degrees(math.atan2(-dy, dx)) - player.angle

last_t = [0]

def idle():
    global wave_delay, wave_active, auto_aim_acc, levelup_timer
    global game_state, _result_recorded

    now       = glutGet(GLUT_ELAPSED_TIME) / 1000.0
    dt        = min(now - last_t[0], 0.05)
    last_t[0] = now

    if game_state == S_LEVELUP:
        levelup_timer -= dt
        if levelup_timer <= 0:
            advance_to_next_round()
            game_state = S_PLAY
        glutPostRedisplay()
        return

    if game_state == S_PLAY:
        player.update(dt)
        ally.update(dt)

        if player.cheat_aim and player.alive:
            auto_aim_acc += dt
            if auto_aim_acc > 0.45:
                auto_aim_acc = 0.0
                auto_aim_fire()

        for e in enemies:
            e.update(dt)

        if boss and boss.alive:
            boss.update(dt)

        for bm in bombs:
            if bm.alive and bm.triggered:
                bm.fuse -= dt
                if bm.fuse <= 0:
                    bm.alive = False

        for b in bullets:
            b.update()
        bullets[:]    = [b  for b  in bullets    if b.alive]
        explosions[:] = [ex for ex in explosions if ex.alive]
        for ex in explosions:
            ex.update(dt)

        check_collisions()
        check_wave_done()

        if current_round == MAX_ROUNDS and boss and not boss.alive:
            check_wave_win()
        else:
            check_win_lose()

        if not wave_active:
            wave_delay -= dt
            if wave_delay <= 0:
                start_wave(wave)

    glutPostRedisplay()

def showScreen():
    th  = ARENAS[arena_sel]
    sky = th["sky"]
    glClearColor(sky[0]*0.45, sky[1]*0.45, sky[2]*0.45, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, WIN_W, WIN_H)

    if game_state in (S_MENU, S_ARENA, S_INSTR, S_OVER, S_SCORES, S_GAMECLEAR):
        glDisable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, WIN_W, 0, WIN_H)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        if game_state == S_MENU:
            draw_menu()
        elif game_state == S_ARENA:
            draw_arena_select()
        elif game_state == S_INSTR:
            draw_instructions()
        elif game_state == S_OVER:
            draw_gameover()
        elif game_state == S_SCORES:
            draw_scores_screen()
        elif game_state == S_GAMECLEAR:
            draw_gameclear_screen()
        glutSwapBuffers()
        return

    if game_state == S_LEVELUP:
        glDisable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, WIN_W, 0, WIN_H)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        draw_levelup_screen()
        glutSwapBuffers()
        return

    glEnable(GL_DEPTH_TEST)
    setupCamera()
    draw_arena()

    for b in bullets:
        draw_bullet(b)
    for ex in explosions:
        draw_explosion(ex)

    if player.alive and not first_person:
        draw_tank(player.x, player.y,
                  player.angle, player.turret_a,
                  player.col, player.hp / player.max_hp,
                  player.shield_on, player.has_flag)

    if ally.alive:
        draw_tank(ally.x, ally.y,
                  ally.angle, 0,
                  (0.28, 0.95, 0.45),
                  ally.hp / ally.max_hp)

    for e in enemies:
        if e.alive:
            draw_tank(e.x, e.y, e.angle, 0,
                      (0.88, 0.15, 0.15),
                      e.hp / e.max_hp, False, e.has_flag)

    # draw boss tank
    if boss and boss.alive:
        t_ms = glutGet(GLUT_ELAPSED_TIME)
        pulse = abs(math.sin(t_ms / 200.0))
        if boss.phase == 2:
            col = (0.9 + 0.1*pulse, 0.05, 0.05)
        else:
            col = (0.75, 0.05, 0.05)
        draw_tank(boss.x, boss.y,
                  boss.angle, 0,
                  col,
                  boss.hp_ratio, False, False, big=True)

    glDisable(GL_DEPTH_TEST)
    draw_hud()
    if game_state == S_PAUSE:
        draw_paused()

    glutSwapBuffers()


def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Siege Tanks: Arena Domination v5 - 5 Rounds + Boss")
    glEnable(GL_DEPTH_TEST)
    last_t[0] = glutGet(GLUT_ELAPSED_TIME) / 1000.0
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutKeyboardUpFunc(keyboardUpListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutPassiveMotionFunc(passiveMotionListener)
    glutIdleFunc(idle)
    glutMainLoop()

if __name__ == "__main__":
    main()