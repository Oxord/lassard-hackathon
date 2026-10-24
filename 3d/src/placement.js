// Размещение подписей отрезков «Луча» на полу: рядом с остановкой, но не на луче и без наложения
// на другие подписи, номера зон и контуры зон. Чистые функции, без three.js.

const PILL_WIDTH = 4.2;
const PILL_HEIGHT = 0.95;
const BEAM_CLEARANCE = 0.3; // половина ширины луча + зазор
const SIDE_OFFSET = PILL_HEIGHT / 2 + BEAM_CLEARANCE;
const NUMBER_HALF = 0.85; // номер зоны в виде сверху занимает до ~1,7 м
const STAND_HALF_W = 0.4; // стойка-штандарт 0,7×0,5 м с запасом
const STAND_HALF_D = 0.3;
const GAP = 0.3;
const SLIDE_STEP = 0.4;
const SLIDE_MAX = 8;
const BEAM_SAMPLE = 0.2;

function lengthsAlong(pts) {
  const acc = [0];
  for (let i = 1; i < pts.length; i++) acc.push(acc[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  return acc;
}

function pointAt(pts, acc, s) {
  const clamped = Math.max(0, Math.min(acc[acc.length - 1], s));
  let i = 1;
  while (i < pts.length - 1 && acc[i] < clamped) i++;
  const [ax, az] = pts[i - 1], [bx, bz] = pts[i];
  const seg = acc[i] - acc[i - 1] || 1;
  const t = (clamped - acc[i - 1]) / seg;
  let angle = Math.atan2(bz - az, bx - ax);
  if (angle > Math.PI / 2) angle -= Math.PI; else if (angle < -Math.PI / 2) angle += Math.PI;
  return { x: ax + (bx - ax) * t, z: az + (bz - az) * t, angle };
}

function arcOfNearest(pts, acc, p) {
  let best = { d: Infinity, s: 0 };
  for (let i = 1; i < pts.length; i++) {
    const [ax, az] = pts[i - 1], [bx, bz] = pts[i];
    const vx = bx - ax, vz = bz - az, l2 = vx * vx + vz * vz || 1;
    const t = Math.max(0, Math.min(1, ((p[0] - ax) * vx + (p[1] - az) * vz) / l2));
    const d = Math.hypot(p[0] - (ax + vx * t), p[1] - (az + vz * t));
    if (d < best.d) best = { d, s: acc[i - 1] + (acc[i] - acc[i - 1]) * t };
  }
  return best.s;
}

function corners({ x, z, hw, hh, angle }) {
  const c = Math.cos(angle), s = Math.sin(angle);
  return [[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]].map(([u, v]) => [x + u * c - v * s, z + u * s + v * c]);
}

function overlaps(a, b) {
  const ca = corners(a), cb = corners(b);
  for (const rect of [a, b]) {
    const c = Math.cos(rect.angle), s = Math.sin(rect.angle);
    for (const [ax, az] of [[c, s], [-s, c]]) {
      const proj = (pts) => pts.map(([px, pz]) => px * ax + pz * az);
      const pa = proj(ca), pb = proj(cb);
      if (Math.max(...pa) + GAP < Math.min(...pb) || Math.max(...pb) + GAP < Math.min(...pa)) return false;
    }
  }
  return true;
}

function insideRect(rect, [px, pz]) {
  const c = Math.cos(rect.angle), s = Math.sin(rect.angle);
  const dx = px - rect.x, dz = pz - rect.z;
  return Math.abs(dx * c + dz * s) <= rect.hw && Math.abs(-dx * s + dz * c) <= rect.hh;
}

function beamSamples(pts, acc) {
  const out = [];
  for (let s = 0; s <= acc[acc.length - 1]; s += BEAM_SAMPLE) {
    const { x, z } = pointAt(pts, acc, s);
    out.push([x, z]);
  }
  return out;
}

function candidates(pts, acc, s0) {
  const list = [];
  for (let d = 0; d <= SLIDE_MAX; d += SLIDE_STEP) {
    for (const along of d === 0 ? [0] : [d, -d]) {
      for (const side of [1, -1]) {
        const at = pointAt(pts, acc, s0 + along);
        const nx = -Math.sin(at.angle) * side, nz = Math.cos(at.angle) * side;
        list.push({ x: at.x + nx * SIDE_OFFSET, z: at.z + nz * SIDE_OFFSET, hw: PILL_WIDTH / 2, hh: PILL_HEIGHT / 2, angle: at.angle });
      }
    }
  }
  return list;
}

/**
 * Возвращает [{x, z, angle}] для каждой подписи (в порядке stops): рядом со своей остановкой, сбоку от луча.
 * beam — ломаная [[x, z], ...]; stops — [[x, z], ...]; zones — зоны из zones.json; bounds — {w, d} зала;
 * standSpots — места стоек-штандартов [[x, z], ...], их тоже не перекрываем.
 */
export function placeFloorPills(beam, stops, zones, bounds, standSpots = []) {
  const acc = lengthsAlong(beam);
  const samples = beamSamples(beam, acc);
  const numbers = zones.map((z) => ({ x: z.x, z: z.z, hw: NUMBER_HALF, hh: NUMBER_HALF, angle: 0 }));
  const footprints = zones.map((z) => ({ x: z.x, z: z.z, hw: z.w / 2, hh: z.d / 2, angle: 0 }));
  const stands = standSpots.map(([x, z]) => ({ x, z, hw: STAND_HALF_W, hh: STAND_HALF_D, angle: 0 }));
  const placed = [];
  const fits = (rect, withFootprints) => (
    corners(rect).every(([px, pz]) => Math.abs(px) <= bounds.w / 2 - 0.3 && Math.abs(pz) <= bounds.d / 2 - 0.3)
    && !placed.some((other) => overlaps(rect, other))
    && !numbers.some((n) => overlaps(rect, n))
    && !stands.some((st) => overlaps(rect, st))
    && !(withFootprints && footprints.some((f) => overlaps(rect, f)))
    && !samples.some((p) => insideRect({ ...rect, hw: rect.hw + 0.1, hh: rect.hh + 0.1 }, p))
  );
  return stops.map((stop) => {
    const options = candidates(beam, acc, arcOfNearest(beam, acc, stop));
    const pick = options.find((o) => fits(o, true)) || options.find((o) => fits(o, false)) || options[0];
    placed.push(pick);
    return { x: pick.x, z: pick.z, angle: pick.angle };
  });
}
