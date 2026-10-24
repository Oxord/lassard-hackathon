"""Генератор планировок шоурума «Лассард». Запуск: python plan/make_plan.py [папка_вывода]

Данные: ../3d/src/zones.json (стороны цеха и офиса, проёмы, колонны — параметры room, ДОПУЩЕНИЕ).
Пишет plan-zones.png, plan-safety.png, plan-flows.png и ../3d/src/routes.json.
Перед отрисовкой прогоняет проверки plan/layout.py; при нарушениях печатает их и выходит с кодом 1.
"""
import json
import os
import sys
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle, FancyArrowPatch  # noqa: E402

import layout  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE
ROUTES_JSON = os.path.join(HERE, '..', '3d', 'src', 'routes.json')

# Палитра из scripts/make_infographics.py: красный и серые, без чёрного
RED, WHITE, GRAY, DARK = '#DD191C', '#FFFFFF', '#7F7F7F', '#595959'
GLASS, EXIT, ROUTE = '#7FB2D9', '#1b9e3a', '#DD191C'
ROLE_GRAY = '#8C8C8C'   # тонкий пунктир маршрутов ролей
BG, BEAM_LW = '#F7F7F7', 7   # светлый фон; толщина красной полосы «Луча»
FILL = {'red': RED, 'white': WHITE, 'gray': GRAY}
SC_COL = {'client': ROLE_GRAY, 'partner': ROLE_GRAY, 'edu': ROLE_GRAY, 'gov': ROLE_GRAY}
LASER_MODELS = ('cutter', 'engraver', 'robot', 'booth')   # зоны с излучением (станки в кожухах, кабина 12)
SHORT = {'Вход: история и география': 'Вход: история', 'Роботизированные ячейки': 'Роботы',
         'Ручные лазерные аппараты: витрина': 'Ручные\nвитрина', 'Закрытая кабина ручных аппаратов': 'Кабина\nручных',
         'Гравировка и маркировка': 'Гравировка', 'Выращивание кристаллов': 'Кристаллы',
         'Лазерные источники': 'Источники', 'Тест-драйв образцов': 'Тест-драйв'}
WIDTH_LABEL_MAX = 6   # шире — подписываем «≥6 м»: пролёт открытого зала, а не ширина прохода
SIDE_RU = {'north': 'север', 'south': 'юг', 'east': 'восток', 'west': 'запад'}


def wall_line(side, room):
    W, D = room['w'], room['d']
    return {'north': ((0, 0), (W, 0)), 'south': ((0, D), (W, D)), 'west': ((0, 0), (0, D)), 'east': ((W, 0), (W, D))}[side]


def outside_label_pos(side, room, off=1.1):
    W, D = room['w'], room['d']
    return {'north': (W / 2, -off), 'south': (W / 2, D + off), 'west': (-off, D / 2), 'east': (W + off, D / 2)}[side]


def draw_room(ax, plan, title):
    room = plan.room
    W, D = room['w'], room['d']
    ax.set_xlim(-3.2, W + 3.2)
    ax.set_ylim(D + 4.6, -3.4)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.add_patch(Rectangle((0, 0), W, D, fc=BG, ec='none', zorder=0))
    for side in layout.SIDES:   # стены: внешняя — толстая чёрная
        (a, b) = wall_line(side, room)
        ext = side in layout.EXTERNAL_WALLS
        ax.plot([a[0], b[0]], [a[1], b[1]], color=DARK if ext else '#555', lw=4 if ext else 2.2, zorder=4, solid_capstyle='butt')
    ax.text(W / 2, -0.35, 'Внешняя стена (сэндвич-панели) — перегородку с цехом не ставим', ha='center', va='bottom', fontsize=7.5, color='#444')
    grid = room['grid']   # разметочная сетка 6 м по осям колонн
    for k in range(int(W // grid) + 1):
        ax.plot([k * grid] * 2, [0, D], color='#d7dae0', lw=0.7, ls='--', zorder=0.5)
    y0 = min(room['columns']['ys']) % grid
    y = y0
    while y <= D:
        ax.plot([0, W], [y, y], color='#d7dae0', lw=0.7, ls='--', zorder=0.5)
        y += grid
    draw_columns(ax, plan)
    draw_partition_and_office(ax, plan)
    draw_openings(ax, plan)
    for a in room.get('service_areas', []):
        r = layout.area_rect(a)
        ax.add_patch(Rectangle((r[0], r[2]), r[1] - r[0], r[3] - r[2], fc='#e4e6ea', ec='#888', hatch='..', lw=0.8, zorder=2))
        ax.text((r[0] + r[1]) / 2, (r[2] + r[3]) / 2, a['name'].replace(': ', ':\n'), ha='center', va='center', fontsize=6.5,
                color='#555', zorder=3, bbox=dict(fc='white', ec='none', alpha=0.8, pad=1))
    ax.set_title(title, fontsize=15, fontweight='bold', color=DARK, pad=4)


def draw_columns(ax, plan):
    room = plan.room
    c = room['columns']
    for x in c['xs']:
        ax.plot([x, x], [-1.7, -0.9], color='#666', lw=0.8)
        ax.text(x, -2.0, 'ABCDEFGH'[c['xs'].index(x)], ha='center', va='bottom', fontsize=9, fontweight='bold', color='#444')
    for a, b in zip(c['xs'], c['xs'][1:]):
        ax.annotate('', (a, -1.3), (b, -1.3), arrowprops=dict(arrowstyle='<->', color='#666', lw=0.8))
        ax.text((a + b) / 2, -1.45, '%d 000' % (b - a), ha='center', va='bottom', fontsize=8, color='#444')
    for j, y in enumerate(c['ys']):
        ax.text(-1.3, y, str(j + 1), ha='center', va='center', fontsize=9, fontweight='bold', color='#444')
    for r in plan.col_bodies:
        ax.add_patch(Rectangle((r[0], r[2]), r[1] - r[0], r[3] - r[2], fc='#6b727c', ec=DARK, lw=0.8, zorder=6))


def draw_partition_and_office(ax, plan):
    room = plan.room
    side = room.get('production_side')
    for t0, t1 in layout.partition_segments(room):
        a, b = layout.wall_point(side, t0, room, 0.15), layout.wall_point(side, t1, room, 0.15)
        ax.plot([a[0], b[0]], [a[1], b[1]], color=GLASS, lw=5, zorder=5, solid_capstyle='butt')
    if side in layout.SIDES and side not in layout.EXTERNAL_WALLS:
        x, y = outside_label_pos(side, room)
        rot = 90 if side in ('east', 'west') else 0
        ax.text(x, y, 'Стекло в цех\n80% локализации · реестр Минпромторга' if side == 'south' else 'ЦЕХ · сторона уточняется',
                ha='center', va='center', rotation=rot, fontsize=8, color=GLASS, fontweight='bold')
    office = room.get('office_side')
    if office in layout.SIDES:
        x, y = outside_label_pos(office, room, 2.0 if office == 'south' else 2.4)
        rot = 90 if office in ('east', 'west') else 0
        ax.text(x, y, 'ОФИС (office_side=%s, ДОПУЩЕНИЕ)' % office, ha='center', va='center', rotation=rot, fontsize=8, color='#555')


def draw_openings(ax, plan):
    room = plan.room
    for o in room['openings']:
        a, b = layout.wall_point(o['wall'], o['from'], room), layout.wall_point(o['wall'], o['to'], room)
        ax.plot([a[0], b[0]], [a[1], b[1]], color='white', lw=5, zorder=5)
        ax.plot([a[0], b[0]], [a[1], b[1]], color=EXIT, lw=3, zorder=6)
        x, y = layout.wall_point(o['wall'], (o['from'] + o['to']) / 2, room, -0.6)
        ax.text(x, y, o['name'].replace(': ', ':\n'), ha='center', va='top' if o['wall'] == 'south' else 'bottom',
                fontsize=7.5, color=EXIT, fontweight='bold', zorder=7)


def draw_zone(ax, plan, i, alpha=1.0):
    z, r = plan.zones[i], plan.rects[i]
    ax.add_patch(Rectangle((r[0], r[2]), r[1] - r[0], r[3] - r[2], fc=FILL[z['kind']], ec=DARK,
                           lw=2.0 if z.get('enclosed') else 1.0, alpha=alpha, zorder=2))
    cx, cy = (r[0] + r[1]) / 2, (r[2] + r[3]) / 2
    tc = 'white' if z['kind'] in ('red', 'gray') and alpha > 0.6 else DARK
    star = '*' if z['dims']['status'] == 'DIM_TBD' else ''
    small = min(r[1] - r[0], r[3] - r[2]) < 2.3
    ax.text(cx, cy - (0.25 if small else 0.45), str(i), ha='center', va='center', fontsize=11 if small else 15,
            fontweight='bold', color=tc, zorder=7)
    name = SHORT.get(z['name'], z['name'])
    ax.text(cx, cy + (0.5 if small else 0.55), name + star, ha='center', va='center', fontsize=5.8 if small else 7.2,
            color=tc, zorder=7, wrap=True)


def arrow(ax, a, b, color, lw=2.2, ls='-'):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=13, color=color, lw=lw, ls=ls, zorder=8))


def draw_polyline(ax, pts, color, lw=2.4, dx=0.0, dy=0.0, ls='-', arrows=True, zorder=7):
    xs, ys = [p[0] + dx for p in pts], [p[1] + dy for p in pts]
    ax.plot(xs, ys, color=color, lw=lw, ls=ls, solid_joinstyle='round', zorder=zorder)
    if arrows:
        for a, b in zip(pts[::3], pts[1::3]):
            if layout.polyline_length([a, b]) > 1.5:
                m = ((a[0] + b[0]) / 2 + dx, (a[1] + b[1]) / 2 + dy)
                arrow(ax, (m[0] - (b[0] - a[0]) * 0.05, m[1] - (b[1] - a[1]) * 0.05), m, color, lw=lw)
        if len(pts) > 1:
            arrow(ax, (xs[-2], ys[-2]), (xs[-1], ys[-1]), color, lw=lw)


def draw_beam(ax, pts):
    """«Луч ЛАССАРД»: красная непрерывная полоса от стены истории к стеклу цеха."""
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=RED, lw=BEAM_LW, solid_joinstyle='round',
            solid_capstyle='round', alpha=0.9, zorder=6)


def draw_legend(ax, plan, role=False):
    items = [ax.plot([], [], color=RED, lw=BEAM_LW / 1.5, label='Луч ЛАССАРД — основной маршрут')[0]]
    if role:
        items.append(ax.plot([], [], color=ROLE_GRAY, lw=1.2, ls='--', label='Маршрут роли (тонкий пунктир)')[0])
    items.append(ax.plot([], [], color=GLASS, lw=5, label='Стекло в цех (юг)')[0])
    room = plan.room   # под линией стекла, правее подписи «Стекло в цех»
    ax.legend(handles=items, loc='upper right', bbox_to_anchor=(room['w'] + 3.2, room['d'] + 0.7), bbox_transform=ax.transData,
              fontsize=8.5, frameon=True, facecolor='white', edgecolor=GRAY)


def footer(ax, plan, lines):
    D = plan.room['d']
    wrapped = [part for line in lines for part in textwrap.wrap(line, width=165)]
    for k, t in enumerate(wrapped):
        ax.text(0, D + 2.9 + k * 0.55, t, fontsize=7.6, color='#444', va='top')


def assumptions_line(plan):
    room = plan.room
    return ('ПРОЕКТНЫЕ ДОПУЩЕНИЯ: зал %g×%g м (626 м² кейса), колонны %g м, цех — %s, офис — %s. Входы/выходы предлагаемые. '
            '* — габарит DIM_TBD (нет в facts.md); зона = габарит + 2×%g м обслуживания.'
            % (room['w'], room['d'], room['columns']['size'], SIDE_RU.get(room.get('production_side'), '?'),
               SIDE_RU.get(room.get('office_side'), '?'), plan.p['service']))


CIRCLED = '①②③④⑤⑥⑦⑧⑨'
STATION = '#ffd400'


def station_point(plan, s):
    """Где рисовать кружок этапа: левый верхний угол зоны или рядом с точкой финала."""
    if s['zone'] == 'finale':
        f = plan.finale()
        return (f[0] - 1.0, f[1] - 0.7)
    r = plan.rects[s['zone']]
    return (r[0], r[2])   # на углу зоны, чтобы не закрывать номер и подпись


def draw_passport(ax, plan):
    for s in plan.data.get('passport_stations', {}).get('stations', []):
        x, y = station_point(plan, s)
        ax.plot(x, y, 'o', ms=17, mfc=STATION, mec=DARK, mew=1.4, zorder=11)
        ax.text(x, y, str(s['n']), ha='center', va='center', fontsize=10, fontweight='bold', color=DARK, zorder=12)


def passport_legend(plan):
    ps = plan.data.get('passport_stations', {})
    parts = [('%s %s' % (CIRCLED[s['n'] - 1], s['text'])) if s['zone'] == 'finale'
             else ('%s зона %s — %s' % (CIRCLED[s['n'] - 1], s['zone'], s['text']))
             for s in ps.get('stations', [])]
    return ['Карта визита и примеры обработки (жёлтые кружки): ' + ' · '.join(parts) + '.',
            'Карта визита не требует сувенира. Изготовление детали при посетителе — дополнительная опция после согласования.']


def plan_zones(plan, report):
    fig, ax = plt.subplots(figsize=(16, 9.4), dpi=120, facecolor='white')
    draw_room(ax, plan, 'ТРИО · «Путь станка» · Предлагаемая планировка после CP2')
    for i in plan.zones:
        draw_zone(ax, plan, i)
    route = report['routes']['all']
    draw_beam(ax, route['points'])
    for s in route['segments']:   # ширина прохода (поперёк) в середине длинных сегментов
        if s['length'] > 4 and not str(s['from']).startswith('проём'):
            a, b = s['points'][len(s['points']) // 2 - 1], s['points'][len(s['points']) // 2]
            p = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            w = plan.grid.span_width(p)
            txt = '≥%g' % WIDTH_LABEL_MAX if w > WIDTH_LABEL_MAX else ('%.1f' % w).replace('.', ',')
            ax.text(p[0], p[1] - 0.35, '↔ %s м' % txt,
                    fontsize=6.5, color='#7a5600', ha='center', zorder=9,
                    bbox=dict(fc='white', ec='none', alpha=0.75, pad=0.6))
    f = plan.finale()
    ax.plot(*f, marker='*', ms=16, color=GLASS, mec=DARK, zorder=9)
    ax.text(f[0], f[1] + 0.9, 'Финал:\nвид на цех', ha='center', va='top', fontsize=7, color=GLASS, fontweight='bold', zorder=9)
    draw_legend(ax, plan)
    draw_passport(ax, plan)
    widths = [s['min_width'] for r in report['routes'].values() for s in r['segments'] if not str(s['from']).startswith('проём') and not str(s['to']).startswith('проём')]
    footer(ax, plan, passport_legend(plan) + [
        'Красный: рабочие зоны 6, 7, 8, 12 · Белый: чистая зона · Серый: техника · жирная рамка: закрытое помещение · '
        'красная полоса: «Луч» с сопровождением; у смотровой точки допускается возврат. Одновременно одна группа.',
        'Подписи — свободная ширина в модели: минимум %s м (проектный порог ≥%s м, группа до %d чел.). Это не нормативный расчет.'
        % (('%.1f' % min(widths)).replace('.', ','), ('%g' % plan.p['aisle_min']).replace('.', ','), plan.p['group_max']),
        assumptions_line(plan)])
    fig.savefig(os.path.join(OUT, 'plan-zones.png'), bbox_inches='tight')
    plt.close(fig)


def plan_safety(plan, report):
    fig, ax = plt.subplots(figsize=(16, 9.4), dpi=120, facecolor='white')
    draw_room(ax, plan, 'Планировка 2. Безопасность: лазерные зоны, вытяжки, эвакуация')
    for i in plan.zones:
        draw_zone(ax, plan, i, alpha=0.35)
    for i, z in plan.zones.items():
        if z['model'] in LASER_MODELS:
            r = plan.rects[i]
            ax.add_patch(Rectangle((r[0], r[2]), r[1] - r[0], r[3] - r[2], fc='none', ec='#d62728', lw=2, hatch='///', zorder=3))
            ax.plot(r[1] - 0.45, r[2] + 0.45, marker='s', ms=11, color='#e377c2', zorder=8)
            ax.text(r[1] - 0.45, r[2] + 0.45, 'В', ha='center', va='center', fontsize=7, color='white', zorder=9, fontweight='bold')
    exits = plan.room['openings']
    dists = {o['id']: plan.grid.distances(layout.opening_point(o, plan.room), plan.evac) for o in exits}
    worst = 0.0
    for i in plan.zones:
        p = plan.stop(i)
        if p is None:
            continue
        c = plan.grid.cell(p)
        o = min(exits, key=lambda o: dists[o['id']][c])
        worst = max(worst, float(dists[o['id']][c]))
        cells = plan.grid.path(p, layout.opening_point(o, plan.room), plan.evac)
        if cells:
            draw_polyline(ax, layout.simplify([plan.grid.point(k) for k in cells], 0.25), EXIT, lw=1.3, ls='--', arrows=False, zorder=6)
            ax.plot(*p, 'o', ms=3.5, color=EXIT, zorder=7)
    footer(ax, plan, [
        '▨ Возможные демонстрации: 6, 7 — только в подтвержденном защитном исполнении; сварка/очистка — в кабине 12 после согласования. '
        'Зона 8 — робот-манипулятор с гравером в защитном ограждении (показ оператором); 9 — обесточенные аппараты и образцы. Без открытого луча в общем зале.',
        '■ В: требуемые точки подключения вытяжки. Схемы вентиляции, пожарной защиты и защиты от лазерного излучения подлежат проектированию.',
        'Пунктир: проверенный в модели путь ≥%s м к предлагаемому выходу; наибольший %s м. Это не утвержденная схема эвакуации.'
        % (('%g' % plan.p['evac_min']).replace('.', ','), ('%.0f' % worst)),
        assumptions_line(plan)])
    fig.savefig(os.path.join(OUT, 'plan-safety.png'), bbox_inches='tight')
    plt.close(fig)


def plan_flows(plan, report):
    fig, ax = plt.subplots(figsize=(16, 9.4), dpi=120, facecolor='white')
    draw_room(ax, plan, 'Четыре сценария на общем маршруте · точки внимания различаются')
    for i in plan.zones:
        draw_zone(ax, plan, i, alpha=0.3)
    draw_beam(ax, report['routes']['all']['points'])
    lane = {'client': (-0.45, -0.45), 'partner': (-0.15, -0.15), 'edu': (0.15, 0.15), 'gov': (0.45, 0.45)}
    for s in plan.data['scenarios']:
        pts = report['routes'][s['id']]['points']
        dx, dy = lane.get(s['id'], (0, 0))
        draw_polyline(ax, pts, SC_COL[s['id']], lw=0.9, dx=dx, dy=dy, ls='--')
        for i in s['zones']:
            p = plan.stop(i)
            ax.plot(p[0] + dx, p[1] + dy, 'o', ms=4.5, color=SC_COL[s['id']], zorder=9)
        ends = 'стекло → 13' if any(plan.zones[i]['model'] == 'meeting' for i in s['zones']) else 'стекло → проём 2'
        ax.plot([], [], color=SC_COL[s['id']], lw=3,
                label='%s: %s' % (s['name'], ' → '.join(str(i) for i in s['zones'] if plan.zones[i]['model'] != 'meeting') + ' → ' + ends))
    draw_passport(ax, plan)
    footer(ax, plan, passport_legend(plan))
    draw_legend(ax, plan, role=True)
    fig.savefig(os.path.join(OUT, 'plan-flows.png'), bbox_inches='tight')
    plt.close(fig)


def write_routes(plan, report):
    room = plan.room
    data = {'note': 'СГЕНЕРИРОВАНО plan/make_plan.py из zones.json — не править руками.',
            'finale': layout.to_scene(plan.finale(), room),
            'stops': {str(i): layout.to_scene(plan.stop(i), room) for i in plan.zones},
            'routes': {k: [layout.to_scene(p, room) for p in r['points']] for k, r in report['routes'].items()}}
    with open(ROUTES_JSON, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write('\n')


def print_report(violations, report):
    print('Проверка планировки: нарушений %d' % len(violations))
    for v in violations:
        print('  НАРУШЕНИЕ:', v)
    for warning in report.get('circulation_warnings', []):
        print('  ОРГАНИЗАЦИЯ ПОТОКА (одна группа с сопровождением):', warning)
    for k, r in report.get('routes', {}).items():
        segs = r['segments']
        if segs:
            print('  маршрут %-8s длина %5.1f м, мин. ширина %.1f м' % (k, sum(s['length'] for s in segs),
                  min(s['min_width'] for s in segs if not str(s['from']).startswith('проём') and not str(s['to']).startswith('проём'))))
    need = report.get('gather_need')
    for i, g in report.get('gather', {}).items():
        kind = 'внутри помещения' if g['inside'] else 'перед зоной'
        fits = 'помещается' if g['area'] >= need else 'НЕ помещается'
        print('  группа у зоны %-2s: %5.1f м² %s (нужно %g) — %s' % (i, g['area'], kind, need, fits))
    for k, d in report.get('evac', {}).items():
        print('  эвакуация от %-11s: %s' % (k, ', '.join('проём %s — %s м' % (o, v) for o, v in d.items())))


def main():
    data = layout.load()
    violations, report, plan = layout.check_all(data)
    print_report(violations, report)
    if plan.finale() is not None and 'all' in report.get('routes', {}):
        plan_zones(plan, report)
        plan_safety(plan, report)
        plan_flows(plan, report)
        write_routes(plan, report)
        print('PNG: %s; маршруты: %s' % (OUT, os.path.normpath(ROUTES_JSON)))
    return 1 if violations else 0


if __name__ == '__main__':
    sys.exit(main())
