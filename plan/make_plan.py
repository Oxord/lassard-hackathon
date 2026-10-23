"""Генератор планировок шоурума «Лассард». Запуск: python3 make_plan.py
Размеры ОЦЕНОЧНЫЕ (36 x 17.4 м), положение перегородки и выходов — предположение. Данные зон берутся из ../3d/src/zones.json.
"""
import json, os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Circle, Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
ZONES = os.path.join(HERE, '..', '3d', 'src', 'zones.json')
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE
data = json.load(open(ZONES, encoding='utf-8'))
W, D = data['room']['w'], data['room']['d']
RED, WHITE, GRAY, DARK = '#c8102e', '#f2f2f2', '#8a9099', '#14161a'
FILL = {'red': RED, 'white': WHITE, 'gray': GRAY}
SC_COL = {'client': '#c8102e', 'partner': '#1f77b4', 'edu': '#2ca02c', 'gov': '#9467bd'}

def base(title):
    fig, ax = plt.subplots(figsize=(16, 8.6), dpi=120)
    ax.set_xlim(-W/2 - 2, W/2 + 2); ax.set_ylim(-D/2 - 4.3, D/2 + 3.2); ax.set_aspect('equal'); ax.axis('off')
    ax.add_patch(Rectangle((-W/2, -D/2), W, D, fc='#fbfbfc', ec=DARK, lw=3))
    for x in range(-18, 19, 6): ax.plot([x, x], [-D/2, D/2], color='#d7dae0', lw=0.8, zorder=0)
    for k in range(4): y = -D/2 + k*D/3; ax.plot([-W/2, W/2], [y, y], color='#d7dae0', lw=0.8, zorder=0)
    for x in range(-12, 19, 6):
        for y in (-D/2 + D/3, D/2 - D/3):
            ax.add_patch(Circle((x, y), 0.35, fc=GRAY, ec=DARK, zorder=3))
    # сетка: подписи
    for i, x in enumerate(range(-15, 16, 6)): ax.text(x, D/2 + 0.5, 'ABCDEF'[i], ha='center', fontsize=9, color='#666')
    for j, y in enumerate((D/3, 0, -D/3)): ax.text(-W/2 - 0.8, y, str(j+1), va='center', fontsize=9, color='#666')
    # перегородка с цехом (северная стена)
    ax.add_patch(Rectangle((-W/2 + 3, D/2 - 0.9), W - 6, 0.35, fc='#88ccff', ec='#3b7ea1', zorder=4))
    ax.text(0, D/2 + 1.3, 'Светопрозрачная перегородка с лазерной защитой → цех (предположение: цех за северной стеной)', ha='center', fontsize=9, color='#3b7ea1')
    ax.set_title(title, fontsize=15, fontweight='bold', color=DARK, pad=6)
    ax.text(W/2 + 1.9, -D/2 - 3.6, 'Размеры оценочные (≈36×17,4 м, сетка колонн 6×6 м). Уточнить у трекера.', ha='right', fontsize=8, color='#777')
    return fig, ax

def py(z): return -z['z']   # ось Y плана = -z из zones.json: зоны 6-11 у северной стены с перегородкой

def zone_rect(ax, z, alpha=1.0, hatch=None, label=True):
    ec = DARK
    ax.add_patch(Rectangle((z['x'] - z['w']/2, py(z) - z['d']/2), z['w'], z['d'], fc=FILL[z['kind']], ec=ec, lw=1.2, alpha=alpha, hatch=hatch, zorder=2))
    if label:
        tc = 'white' if (z['kind'] in ('red', 'gray') and alpha > 0.6) else DARK
        ax.text(z['x'], py(z) + 0.5, str(z['id']), ha='center', va='center', fontsize=17, fontweight='bold', color=tc, zorder=5)
        name = z['name'].replace('Роботизированные ячейки', 'Роботы').replace('Ручные лазерные аппараты', 'Ручные аппараты').replace('Вход: история и география', 'Вход: история')
        ax.text(z['x'], py(z) - 0.9, name, ha='center', va='center', fontsize=8.5, color=tc, zorder=5)

def pt(z, off=0.0):  # точка маршрута на проходе (к центру зала)
    y = py(z)
    return (z['x'], y + (2.9 + off if y < 0 else -2.9 - off))

def arrow(ax, a, b, color, lw=2.4, ls='-', rad=0.0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=16, color=color, lw=lw, ls=ls, connectionstyle=f'arc3,rad={rad}', zorder=6))

zones = data['zones']; zid = {z['id']: z for z in zones}

# 1) зонирование + маршрут
fig, ax = base('Планировка 1. Зонирование и маршрут «Путь станка»')
for z in zones: zone_rect(ax, z)
ids = [z['id'] for z in zones]
pts = [pt(zid[i]) for i in ids]
for a, b in zip(pts, pts[1:]): arrow(ax, a, b, '#ffb000')
ax.text(-W/2 - 1.9, -D/2 - 2.9, 'Красный: рабочая зона · Белый: декоративная · Серый: технические элементы', fontsize=8.5, color='#444')
ax.annotate('ВХОД', (-15, -D/2), (-15, -D/2 - 1.9), ha='center', fontsize=11, fontweight='bold', color=RED, arrowprops=dict(arrowstyle='->', color=RED, lw=2))
fig.savefig(os.path.join(OUT, 'plan-zones.png'), bbox_inches='tight'); plt.close(fig)

# 2) безопасность
fig, ax = base('Планировка 2. Безопасность: пожаротушение, вытяжки, эвакуация')
for z in zones: zone_rect(ax, z, alpha=0.35)
for i in (6, 7, 8, 9, 10):
    z = zid[i]
    ax.add_patch(Rectangle((z['x'] - z['w']/2, py(z) - z['d']/2), z['w'], z['d'], fc='none', ec='#d62728', lw=2, hatch='///', zorder=3))
    ax.plot(z['x'], py(z) - 1.9, marker='s', ms=12, color='#e377c2', zorder=6)
    ax.text(z['x'], py(z) - 1.9, 'В', ha='center', va='center', fontsize=7, color='white', zorder=7, fontweight='bold')
def door(x, y, t, horiz):
    w, h = (1.8, 0.5) if horiz else (0.5, 1.8)
    ax.add_patch(Rectangle((x - w/2, y - h/2), w, h, fc='#2ca02c', ec=DARK, zorder=7))
door(-W/2, 3.0, '', False); ax.text(-W/2 - 0.3, 3.0, 'Выход 1', ha='right', va='center', fontsize=8, color='#1b7a1b', fontweight='bold')
door(W/2, -3.0, '', False); ax.text(W/2 + 0.3, -3.0, 'Выход 2', ha='left', va='center', fontsize=8, color='#1b7a1b', fontweight='bold')
door(-15, -D/2, '', True); ax.text(-15, -D/2 - 0.9, 'Вход / выход 3', ha='center', fontsize=8, color='#1b7a1b', fontweight='bold')
door(9, -D/2, '', True); ax.text(9, -D/2 - 0.9, 'Выход 4', ha='center', fontsize=8, color='#1b7a1b', fontweight='bold')
for src, dst in [((-12, 1.2), (-W/2 + 0.6, 3.0)), ((14, -1.2), (W/2 - 0.6, -3.0)), ((-15, -2.2), (-15, -D/2 + 0.6)), ((9, -2.2), (9, -D/2 + 0.6))]:
    arrow(ax, src, dst, '#2ca02c', ls='--', lw=2)
ax.text(-W/2, -D/2 - 2.0, '▨ Автоматическое пожаротушение: зоны лазерной обработки 6–10', color='#d62728', fontsize=9)
ax.text(-W/2, -D/2 - 2.7, '■ В: локальная вытяжка · зелёный прямоугольник: эвакуационный выход · пунктир: эвакуация · маршрут посетителей не пересекает рабочие зоны', color='#444', fontsize=8.5)
fig.savefig(os.path.join(OUT, 'plan-safety.png'), bbox_inches='tight'); plt.close(fig)

# 3) потоки аудиторий: движение строго по проходам, переход между рядами у восточной стены
fig, ax = base('Планировка 3. Маршруты четырёх аудиторий')
for z in zones: zone_rect(ax, z, alpha=0.28)
lane = {'client': 0.0, 'partner': 0.7, 'edu': 1.4, 'gov': 2.1}
def route(ids, k):
    pts = []
    for n, i in enumerate(ids):
        z = zid[i]; p = pt(z, lane[k])
        if pts and (pts[-1][1] < 0) != (p[1] < 0):      # переход между рядами
            xc = 16.2 + lane[k] * 0.5
            pts += [(xc, pts[-1][1]), (xc, p[1])]
        pts.append(p)
    return pts
for s_ in data['scenarios']:
    pts = route(s_['zones'], s_['id'])
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=SC_COL[s_['id']], lw=2.6, solid_joinstyle='round', zorder=6)
    ax.annotate('', pts[-1], pts[-2], arrowprops=dict(arrowstyle='-|>', color=SC_COL[s_['id']], lw=2.6), zorder=7)
    for i in s_['zones']:
        p = pt(zid[i], lane[s_['id']]); ax.plot(*p, 'o', ms=5, color=SC_COL[s_['id']], zorder=8)
    ax.plot([], [], color=SC_COL[s_['id']], lw=3, label=f"{s_['name']}: " + '→'.join(str(i) for i in s_['zones']))
ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.14), ncol=2, fontsize=9, frameon=False)
fig.savefig(os.path.join(OUT, 'plan-flows.png'), bbox_inches='tight'); plt.close(fig)
print('ok')
