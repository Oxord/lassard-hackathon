"""Геометрия и проверки планировки шоурума «Лассард».

Данные: ../3d/src/zones.json. Система координат плана: X — метры от западной стены,
Y — метры от северной стены (в zones.json центр зоны x,z от центра зала, север = −z).
Все пороги берутся из room.params (там же пометки ДОПУЩЕНИЕ / ПРОВЕРИТЬ).
"""
import json
import math
import os
from collections import deque

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ZONES_JSON = os.path.join(HERE, '..', '3d', 'src', 'zones.json')

RES = 0.1                      # шаг растра, м
SIDES = ('north', 'south', 'east', 'west')
EXTERNAL_WALLS = ('north',)    # кейс, слайд 6: внешняя стена (сэндвич-панели), двери на ней зачёркнуты
STOP_OFFSET = 1.5              # точка остановки группы: от фронта зоны, м
STOP_SNAP_MAX = 1.0            # насколько можно сдвинуть точку остановки к оси прохода, м
FINALE_OFFSET = 2.5            # точка финала: от перегородки с цехом внутрь зала, м
FINALE_SNAP_MAX = 2.5
OPENING_POINT_OFFSET = 1.2     # точка у проёма внутри зала, м
SIMPLIFY_TOL = 0.15            # упрощение полилиний маршрута, м


def load(path=ZONES_JSON):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


# ---------- прямоугольники ----------

def zone_rect(z, room):
    """(x0, x1, y0, y1) зоны в координатах плана."""
    cx, cy = z['x'] + room['w'] / 2, z['z'] + room['d'] / 2
    return (cx - z['w'] / 2, cx + z['w'] / 2, cy - z['d'] / 2, cy + z['d'] / 2)


def area_rect(a):
    return (a['x0'], a['x1'], a['y0'], a['y1'])


def grow(r, m):
    return (r[0] - m, r[1] + m, r[2] - m, r[3] + m)


def intersects(a, b, eps=1e-6):
    return a[0] < b[1] - eps and b[0] < a[1] - eps and a[2] < b[3] - eps and b[2] < a[3] - eps


def shared_edge(a, b, gap):
    """Длина общей стороны двух прямоугольников, если между ними не больше gap."""
    if abs(a[3] - b[2]) <= gap or abs(b[3] - a[2]) <= gap:
        return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    if abs(a[1] - b[0]) <= gap or abs(b[1] - a[0]) <= gap:
        return max(0.0, min(a[3], b[3]) - max(a[2], b[2]))
    return 0.0


def touches_wall(r, side, room, gap):
    W, D = room['w'], room['d']
    return {'north': r[2] <= gap, 'south': r[3] >= D - gap,
            'west': r[0] <= gap, 'east': r[1] >= W - gap}[side]


def columns(room):
    c = room['columns']
    return [(x, y) for x in c['xs'] for y in c['ys']]


def column_rect(c, room, clearance=0.0):
    h = room['columns']['size'] / 2 + clearance
    return (c[0] - h, c[0] + h, c[1] - h, c[1] + h)


# ---------- стены, проёмы, перегородка ----------

def wall_length(side, room):
    return room['w'] if side in ('north', 'south') else room['d']


def wall_point(side, t, room, inset=0.0):
    """Точка на стене side на расстоянии t вдоль неё, сдвинутая внутрь на inset."""
    W, D = room['w'], room['d']
    return {'north': (t, inset), 'south': (t, D - inset),
            'west': (inset, t), 'east': (W - inset, t)}[side]


def opening_point(op, room, inset=OPENING_POINT_OFFSET):
    return wall_point(op['wall'], (op['from'] + op['to']) / 2, room, inset)


def opening_clear_rect(op, room):
    """Площадка перед проёмом, которая должна быть свободной."""
    depth = room['params']['opening_depth']
    (ax, ay), (bx, by) = wall_point(op['wall'], op['from'], room), wall_point(op['wall'], op['to'], room, depth)
    return (min(ax, bx), max(ax, bx), min(ay, by), max(ay, by))


def wall_columns(side, room):
    """Позиции колонн, стоящих в стене side, вдоль этой стены."""
    W, D = room['w'], room['d']
    if side in ('west', 'east'):
        x = 0 if side == 'west' else W
        return sorted(c[1] for c in columns(room) if abs(c[0] - x) < 1e-6)
    y = 0 if side == 'north' else D
    return sorted(c[0] for c in columns(room) if abs(c[1] - y) < 1e-6)


def partition_segments(room):
    """Отрезки светопрозрачной перегородки (t0, t1) вдоль стены production_side."""
    side = room.get('production_side')
    if side not in SIDES or side in EXTERNAL_WALLS:
        return []
    h = room['columns']['size'] / 2
    cuts = [(c - h, c + h) for c in wall_columns(side, room)]
    cuts += [(o['from'], o['to']) for o in room['openings'] if o['wall'] == side]
    segs, t = [], 0.0
    for a, b in sorted(cuts):
        if a > t:
            segs.append((t, a))
        t = max(t, b)
    if t < wall_length(side, room):
        segs.append((t, wall_length(side, room)))
    return [s for s in segs if s[1] - s[0] > 0.5]


# ---------- растр и проходы ----------

class Grid:
    def __init__(self, room, obstacles):
        self.room = room
        self.nx, self.ny = int(round(room['w'] / RES)), int(round(room['d'] / RES))
        self.occ = np.zeros((self.ny, self.nx), bool)
        for r in obstacles:
            self.fill(r)
        self._erosions = {}

    def fill(self, r):
        x0, x1 = max(0, int(round(r[0] / RES))), min(self.nx, int(round(r[1] / RES)))
        y0, y1 = max(0, int(round(r[2] / RES))), min(self.ny, int(round(r[3] / RES)))
        if x1 > x0 and y1 > y0:
            self.occ[y0:y1, x0:x1] = True

    def cell(self, p):
        return (min(self.ny - 1, max(0, int(p[1] / RES))), min(self.nx - 1, max(0, int(p[0] / RES))))

    @staticmethod
    def point(c):
        return ((c[1] + 0.5) * RES, (c[0] + 0.5) * RES)

    def free(self, width):
        """Маска клеток, через которые проходит полоса ширины width (квадрат стороной ≥ width)."""
        k = max(0, math.ceil((width / RES - 1) / 2 - 1e-9))
        if k not in self._erosions:
            self._erosions[k] = self._erode(k)
        return self._erosions[k]

    def _erode(self, k):
        pad = np.pad(self.occ, k, constant_values=True).astype(np.int32)
        P = np.pad(pad.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        n = 2 * k + 1
        s = P[n:, n:] - P[:-n, n:] - P[n:, :-n] + P[:-n, :-n]
        return s == 0

    def width_map(self, max_width=8.0):
        """Для каждой свободной клетки — ширина самой широкой полосы, проходящей через неё."""
        wm = np.zeros(self.occ.shape)
        k = 0
        while (2 * k + 1) * RES <= max_width:
            m = self._erosions.get(k)
            if m is None:
                m = self._erosions[k] = self._erode(k)
            if not m.any():
                break
            wm[m] = (2 * k + 1) * RES
            k += 1
        return wm

    def snap(self, p, mask, max_dist):
        c = self.cell(p)
        if mask[c]:
            return p
        ys, xs = np.nonzero(mask)
        if not len(ys):
            return None
        d = (ys - c[0]) ** 2 + (xs - c[1]) ** 2
        i = int(d.argmin())
        if math.sqrt(d[i]) * RES > max_dist:
            return None
        return self.point((ys[i], xs[i]))

    def path(self, a, b, mask):
        """Кратчайший путь (8-связность) по маске; список точек или None."""
        start, goal = self.cell(a), self.cell(b)
        if not (mask[start] and mask[goal]):
            return None
        prev = {start: None}
        q = deque([start])
        while q:
            u = q.popleft()
            if u == goal:
                break
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    v = (u[0] + dy, u[1] + dx)
                    if 0 <= v[0] < self.ny and 0 <= v[1] < self.nx and mask[v] and v not in prev:
                        prev[v] = u
                        q.append(v)
        if goal not in prev:
            return None
        cells, u = [], goal
        while u is not None:
            cells.append(u)
            u = prev[u]
        return cells[::-1]

    def distances(self, src, mask):
        """Длина пути (м) от точки src до всех клеток маски."""
        INF = np.inf
        dist = np.full(self.occ.shape, INF)
        s = self.cell(src)
        if not mask[s]:
            return dist
        dist[s] = 0.0
        q = deque([s])
        while q:
            u = q.popleft()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    v = (u[0] + dy, u[1] + dx)
                    if 0 <= v[0] < self.ny and 0 <= v[1] < self.nx and mask[v] and dist[v] == INF:
                        dist[v] = dist[u] + RES * (1.4142 if dy and dx else 1.0)
                        q.append(v)
        return dist


def simplify(points, tol=SIMPLIFY_TOL):
    """Рамер — Дуглас — Пекер."""
    if len(points) < 3:
        return list(points)
    (ax, ay), (bx, by) = points[0], points[-1]
    L = math.hypot(bx - ax, by - ay) or 1e-9
    dmax, imax = 0.0, 0
    for i, (px, py) in enumerate(points[1:-1], 1):
        d = abs((bx - ax) * (ay - py) - (ax - px) * (by - ay)) / L
        if d > dmax:
            dmax, imax = d, i
    if dmax <= tol:
        return [points[0], points[-1]]
    return simplify(points[:imax + 1], tol)[:-1] + simplify(points[imax:], tol)


def polyline_length(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


# ---------- модель планировки ----------

class Plan:
    def __init__(self, data):
        self.data, self.room = data, data['room']
        self.p = self.room['params']
        self.zones = {z['id']: z for z in data['zones']}
        self.rects = {i: zone_rect(z, self.room) for i, z in self.zones.items()}
        self.service = [area_rect(a) for a in self.room.get('service_areas', [])]
        self.col_bodies = [column_rect(c, self.room) for c in columns(self.room)]
        self.grid = Grid(self.room, list(self.rects.values()) + self.service + self.col_bodies)
        self.aisle = self.grid.free(self.p['aisle_min'])
        self.evac = self.grid.free(self.p['evac_min'])

    def by_model(self, model):
        return [i for i, z in self.zones.items() if z['model'] == model]

    def front_segment(self, i):
        x0, x1, y0, y1 = self.rects[i]
        return {'N': ((x0, y0), (x1, y0)), 'S': ((x0, y1), (x1, y1)),
                'W': ((x0, y0), (x0, y1)), 'E': ((x1, y0), (x1, y1))}[self.zones[i]['front']]

    def front_normal(self, i):
        return {'N': (0, -1), 'S': (0, 1), 'W': (-1, 0), 'E': (1, 0)}[self.zones[i]['front']]

    def stop_raw(self, i):
        (ax, ay), (bx, by) = self.front_segment(i)
        nx, ny = self.front_normal(i)
        return ((ax + bx) / 2 + nx * STOP_OFFSET, (ay + by) / 2 + ny * STOP_OFFSET)

    def stop(self, i):
        return self.grid.snap(self.stop_raw(i), self.aisle, STOP_SNAP_MAX)

    def finale_raw(self):
        segs = partition_segments(self.room)
        if not segs:
            return None
        t0, t1 = max(segs, key=lambda s: s[1] - s[0])
        return wall_point(self.room['production_side'], (t0 + t1) / 2, self.room, FINALE_OFFSET)

    def finale(self):
        p = self.finale_raw()
        return self.grid.snap(p, self.aisle, FINALE_SNAP_MAX) if p else None

    def openings(self, role=None):
        return [o for o in self.room['openings'] if role is None or o['role'] == role]

    def gather_area(self, i):
        """Свободная площадь не дальше gather_depth от фронта зоны, перед фронтом (м²)."""
        g = self.grid
        (ax, ay), (bx, by) = self.front_segment(i)
        nx, ny = self.front_normal(i)
        depth = self.p['gather_depth']
        ys, xs = np.mgrid[0:g.ny, 0:g.nx]
        px, py = (xs + 0.5) * RES, (ys + 0.5) * RES
        ex, ey = bx - ax, by - ay
        t = np.clip(((px - ax) * ex + (py - ay) * ey) / (ex * ex + ey * ey), 0, 1)
        d = np.hypot(px - (ax + t * ex), py - (ay + t * ey))
        ahead = (px - ax) * nx + (py - ay) * ny > 0
        return float(((d <= depth) & ahead & ~g.occ).sum() * RES * RES)

    def scenario_points(self, ids):
        """Точки маршрута: вход → остановки → стекло цеха → переговорная или выход."""
        meeting = set(self.by_model('meeting'))
        ent = self.openings('entrance')
        pts = [('проём %d' % ent[0]['id'], opening_point(ent[0], self.room))] if ent else []
        body = [i for i in ids if i not in meeting]
        pts += [(i, self.stop(i)) for i in body]
        pts.append(('стекло цеха', self.finale()))
        ends = [i for i in ids if i in meeting]
        if ends:
            pts += [(i, self.stop(i)) for i in ends]
        else:
            ex = self.openings('exit')
            if ex:
                pts.append(('проём %d' % ex[0]['id'], opening_point(ex[0], self.room)))
        return pts


# ---------- проверки ----------

def check_room(plan):
    room, v = plan.room, []
    ps, os_ = room.get('production_side'), room.get('office_side')
    if ps not in SIDES:
        v.append('production_side=%r: ожидается одно из %s' % (ps, SIDES))
    elif ps in EXTERNAL_WALLS:
        v.append('production_side=%s: стена внешняя, перегородку с цехом на ней не ставим' % ps)
    elif not partition_segments(room):
        v.append('production_side=%s: на стене нет места под перегородку' % ps)
    if os_ not in SIDES:
        v.append('office_side=%r: ожидается одно из %s' % (os_, SIDES))
    elif os_ in EXTERNAL_WALLS:
        v.append('office_side=%s: стена внешняя' % os_)
    roles = [o['role'] for o in room['openings']]
    if roles.count('entrance') != 1 or 'exit' not in roles:
        v.append('проёмы: нужен один вход (entrance) и хотя бы один выход (exit), сейчас %s' % roles)
    for o in room['openings']:
        if o['wall'] in EXTERNAL_WALLS:
            v.append('проём %s: стена %s внешняя' % (o['id'], o['wall']))
        if not 0 <= o['from'] < o['to'] <= wall_length(o['wall'], room):
            v.append('проём %s: from/to вне стены' % o['id'])
    return v


def check_geometry(plan):
    room, v = plan.room, []
    W, D, cl = room['w'], room['d'], room['columns']['clearance']
    items = list(plan.rects.items()) + [('служебное %d' % n, r) for n, r in enumerate(plan.service)]
    for i, r in items:
        if r[0] < 0 or r[2] < 0 or r[1] > W or r[3] > D:
            v.append('зона %s выходит за зал' % i)
        enclosed = i in plan.zones and plan.zones[i].get('enclosed')
        for c in columns(room):
            if intersects(r, column_rect(c, room)):
                v.append('зона %s пересекает колонну (%g; %g)' % (i, c[0], c[1]))
            elif not enclosed and intersects(r, column_rect(c, room, cl)):
                v.append('зона %s ближе %g м к колонне (%g; %g)' % (i, cl, c[0], c[1]))
    for n, (i, a) in enumerate(items):
        for j, b in items[n + 1:]:
            if intersects(a, b):
                v.append('зоны %s и %s пересекаются' % (i, j))
    for o in room['openings']:
        clear = opening_clear_rect(o, room)
        for i, r in items:
            if intersects(r, clear):
                v.append('зона %s перекрывает площадку перед проёмом %s' % (i, o['id']))
    return v


def check_dims(plan):
    v, s = [], plan.p['service']
    for i, z in plan.zones.items():
        e = z['dims']['equip']
        add = 0 if z.get('service_inside') else 2 * s
        need = (e[0] + add, e[1] + add)
        if not ((z['w'] >= need[0] - 1e-6 and z['d'] >= need[1] - 1e-6) or
                (z['w'] >= need[1] - 1e-6 and z['d'] >= need[0] - 1e-6)):
            v.append('зона %s: %g×%g меньше габарита %g×%g + обслуживание' % (i, z['w'], z['d'], e[0], e[1]))
        f = z.get('field')
        if f and not ((e[0] >= f[0] and e[1] >= f[1]) or (e[0] >= f[1] and e[1] >= f[0])):
            v.append('зона %s: габарит %s меньше рабочего поля %s' % (i, e, f))
    return v


def check_adjacency(plan):
    room, v = plan.room, []
    gap = plan.p.get('wall_gap', 0.3)
    door = plan.p.get('door_min', 1.0)
    for m in plan.by_model('meeting'):
        if room.get('office_side') in SIDES and not touches_wall(plan.rects[m], room['office_side'], room, gap):
            v.append('переговорная %s не примыкает к office_side=%s' % (m, room['office_side']))
        desks = plan.by_model('sampledesk')
        if desks and max(shared_edge(plan.rects[m], plan.rects[t], gap) for t in desks) < door:
            v.append('переговорная %s не примыкает к тест-драйву (общая стена < %g м)' % (m, door))
    for t in plan.by_model('sampledesk'):
        for u in plan.zones[t].get('uses', []):
            if shared_edge(plan.rects[t], plan.rects[u], gap) <= 0:
                v.append('тест-драйв %s не примыкает к зоне %s' % (t, u))
    return v


def check_routes(plan, report):
    """Каждый сегмент каждого сценария — по полосе ≥ aisle_min (у проёмов ≥ evac_min)."""
    v, wm = [], plan.grid.width_map()
    report['routes'] = {}
    for s in plan.data['scenarios']:
        pts = plan.scenario_points(s['zones'])
        bad = [str(k) for k, p in pts if p is None]
        if bad:
            v.append('%s: нет точки остановки на проходе ≥%g м у %s' % (s['id'], plan.p['aisle_min'], ', '.join(bad)))
            continue
        line, segs = [], []
        for (ka, a), (kb, b) in zip(pts, pts[1:]):
            near_door = str(ka).startswith('проём') or str(kb).startswith('проём')
            mask = plan.evac if near_door else plan.aisle
            cells = plan.grid.path(a, b, mask)
            if cells is None:
                v.append('%s: %s → %s нет прохода ≥%g м' % (s['id'], ka, kb, plan.p['evac_min' if near_door else 'aisle_min']))
                continue
            width = float(min(wm[c] for c in cells))
            seg = simplify([plan.grid.point(c) for c in cells])
            segs.append({'from': ka, 'to': kb, 'min_width': round(width, 1), 'length': round(polyline_length(seg), 1)})
            line += seg if not line else seg[1:]
        report['routes'][s['id']] = {'points': line, 'segments': segs}
    return v


def check_gathering(plan, report):
    """Площадка для группы у зон групповых сценариев (не у закрытых комнат)."""
    v, need = [], plan.p['group_max'] * plan.p['m2_per_person']
    groups = plan.p.get('group_scenarios', [])
    ids = sorted({i for s in plan.data['scenarios'] if s['id'] in groups for i in s['zones']})
    report['gather'] = {}
    for i in ids:
        z = plan.zones[i]
        if z.get('enclosed'):
            report['gather'][i] = {'area': round(z['w'] * z['d'], 1), 'inside': True}
            continue
        a = plan.gather_area(i)
        report['gather'][i] = {'area': round(a, 1), 'inside': False}
        if a < need - 1e-6:
            v.append('зона %s: площадка для группы %.1f м² < %g м²' % (i, a, need))
    report['gather_need'] = need
    return v


def check_evacuation(plan, report):
    """Из каждой остановки и точки финала — путь ≥ evac_min к каждому проёму."""
    v, report['evac'] = [], {}
    dists = {o['id']: plan.grid.distances(opening_point(o, plan.room), plan.evac) for o in plan.room['openings']}
    points = [(i, plan.stop(i)) for i in plan.zones] + [('стекло цеха', plan.finale())]
    for k, p in points:
        if p is None:
            continue
        c = plan.grid.cell(p)
        report['evac'][k] = {o: (None if math.isinf(d[c]) else round(float(d[c]), 1)) for o, d in dists.items()}
        missing = [str(o) for o, d in report['evac'][k].items() if d is None]
        if missing:
            v.append('%s: нет пути эвакуации ≥%g м к проёму %s' % (k, plan.p['evac_min'], ', '.join(missing)))
    return v


def check_all(data):
    """Возвращает (нарушения, отчёт, plan)."""
    plan, report = Plan(data), {}
    room_violations = check_room(plan)
    violations = room_violations + check_geometry(plan) + check_dims(plan) + check_adjacency(plan)
    if plan.finale() is None and not room_violations:
        violations.append('нет точки финала у перегородки с цехом на проходе ≥%g м' % plan.p['aisle_min'])
    violations += check_routes(plan, report) + check_gathering(plan, report) + check_evacuation(plan, report)
    return violations, report, plan


def to_scene(p, room):
    """Точка плана → (x, z) в координатах 3D-сцены."""
    return [round(p[0] - room['w'] / 2, 2), round(p[1] - room['d'] / 2, 2)]
