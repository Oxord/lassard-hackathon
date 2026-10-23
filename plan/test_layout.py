"""Тесты геометрии и проверок планировки. Запуск: python plan/test_layout.py"""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout  # noqa: E402

DATA = layout.load()


def mutated(fn):
    d = copy.deepcopy(DATA)
    fn(d)
    return d


def zone(d, i):
    return next(z for z in d['zones'] if z['id'] == i)


class RectTests(unittest.TestCase):
    def test_touching_rects_do_not_intersect(self):
        self.assertFalse(layout.intersects((0, 1, 0, 1), (1, 2, 0, 1)))

    def test_overlapping_rects_intersect(self):
        self.assertTrue(layout.intersects((0, 1, 0, 1), (0.5, 2, 0.5, 2)))

    def test_shared_edge_length(self):
        self.assertAlmostEqual(layout.shared_edge((0, 3, 0, 2), (1, 5, 2.1, 4), 0.3), 2.0)
        self.assertEqual(layout.shared_edge((0, 3, 0, 2), (1, 5, 2.5, 4), 0.3), 0.0)


class GridTests(unittest.TestCase):
    ROOM = {'w': 10, 'd': 6}

    def corridor(self, gap):
        top = (0, 10, 0, 3 - gap / 2)
        bottom = (0, 10, 3 + gap / 2, 6)
        g = layout.Grid(self.ROOM, [top, bottom])
        return g, g.free(3.0)

    def test_corridor_narrower_than_aisle_is_blocked(self):
        g, mask = self.corridor(2.9)
        self.assertFalse(mask.any())

    def test_corridor_wide_enough_has_path(self):
        g, mask = self.corridor(3.2)
        self.assertIsNotNone(g.path((2, 3), (8, 3), mask))

    def test_width_map_reports_corridor_width(self):
        g, _ = self.corridor(3.2)
        self.assertGreaterEqual(g.width_map()[g.cell((5, 3))], 3.0)

    def test_simplify_keeps_endpoints_of_straight_line(self):
        self.assertEqual(layout.simplify([(0, 0), (1, 0.01), (2, 0)]), [(0, 0), (2, 0)])


class PartitionTests(unittest.TestCase):
    def test_glass_skips_wall_columns(self):
        segs = layout.partition_segments(DATA['room'])
        h = DATA['room']['columns']['size'] / 2
        for y in DATA['room']['columns']['ys']:
            self.assertFalse(any(a < y + h and y - h < b for a, b in segs))

    def test_no_glass_on_external_wall(self):
        d = mutated(lambda d: d['room'].update(production_side='north'))
        self.assertEqual(layout.partition_segments(d['room']), [])


class PlanChecksTests(unittest.TestCase):
    def test_current_layout_has_no_violations(self):
        violations, report, _ = layout.check_all(DATA)
        self.assertEqual(violations, [])
        self.assertEqual(set(report['routes']), {s['id'] for s in DATA['scenarios']})

    def test_route_segments_meet_aisle_width(self):
        _, report, plan = layout.check_all(DATA)
        for r in report['routes'].values():
            for s in r['segments']:
                door = str(s['from']).startswith('проём') or str(s['to']).startswith('проём')
                need = plan.p['evac_min'] if door else plan.p['aisle_min']
                self.assertGreaterEqual(s['min_width'], need, s)

    def test_production_on_external_wall_is_rejected(self):
        d = mutated(lambda d: d['room'].update(production_side='north'))
        self.assertTrue(any('внешняя' in v for v in layout.check_all(d)[0]))

    def test_meeting_room_must_touch_office_side(self):
        d = mutated(lambda d: d['room'].update(office_side='west'))
        self.assertTrue(any('office_side' in v for v in layout.check_all(d)[0]))

    def test_zone_on_column_is_rejected(self):
        def move(d):
            z = zone(d, 6)
            z['x'], z['z'] = 12.0 - 18, 14.0 - 8.7 - 1.0
        self.assertTrue(any('колонн' in v for v in layout.check_all(mutated(move))[0]))

    def test_zone_blocking_opening_is_rejected(self):
        def move(d):
            z = zone(d, 13)
            z['x'] = 32.5 - 18
        self.assertTrue(any('проёмом 2' in v or 'пересекаются' in v for v in layout.check_all(mutated(move))[0]))

    def test_zone_smaller_than_equipment_is_rejected(self):
        d = mutated(lambda d: zone(d, 9).update(d=3.0, z=1.8 - 8.7))
        self.assertTrue(any('зона 9' in v and 'габарит' in v for v in layout.check_all(d)[0]))

    def test_production_side_change_moves_finale(self):
        d = mutated(lambda d: d['room'].update(production_side='west'))
        _, _, plan = layout.check_all(d)
        f = plan.finale_raw()
        self.assertLess(f[0], d['room']['w'] / 2)


if __name__ == '__main__':
    unittest.main(verbosity=1)
