// Зал из параметров room (zones.json): колонны, разметка, стены, перегородка с цехом, проёмы.
// Смена production_side / office_side / openings в zones.json перестраивает сцену без правки кода.
import * as THREE from 'three';
import { LIGHT, WHITE, GRAY, GRAY_DARK, GLASS } from './palette.js';
import { standingPlaque } from './decals.js';

// ДОПУЩЕНИЕ: табличка у стекла стоит в просвете между зонами 13 и 11 (x = −3,4 м от центра зала), куда ведёт конец «Луча»
const PLAQUE_T = 18 - 3.4;
const EXTERNAL_WALLS = ['north']; // кейс, слайд 6: внешняя стена из сэндвич-панелей
const SIDE_RU = { north: 'север', south: 'юг', east: 'восток', west: 'запад' };

// Точка на стене side на расстоянии t (м) вдоль неё → координаты сцены (x, z); inset — внутрь зала
export function wallPoint(room, side, t, inset = 0) {
  const { w: W, d: D } = room;
  const p = { north: [t, inset], south: [t, D - inset], west: [inset, t], east: [W - inset, t] }[side];
  return [p[0] - W / 2, p[1] - D / 2];
}

const wallLength = (room, side) => (side === 'north' || side === 'south' ? room.w : room.d);

function wallColumns(room, side) {
  const { xs, ys } = room.columns;
  if (side === 'west' || side === 'east') return xs.includes(side === 'west' ? 0 : room.w) ? ys : [];
  return ys.includes(side === 'north' ? 0 : room.d) ? xs : [];
}

// Отрезки перегородки [t0, t1] вдоль стены цеха — между колоннами и проёмами (как plan/layout.py)
export function partitionSegments(room) {
  const side = room.production_side;
  if (!SIDE_RU[side] || EXTERNAL_WALLS.includes(side)) return [];
  const h = room.columns.size / 2;
  const cuts = wallColumns(room, side).map((c) => [c - h, c + h])
    .concat(room.openings.filter((o) => o.wall === side).map((o) => [o.from, o.to]))
    .sort((a, b) => a[0] - b[0]);
  const segs = [];
  let t = 0;
  for (const [a, b] of cuts) { if (a > t) segs.push([t, a]); t = Math.max(t, b); }
  if (t < wallLength(room, side)) segs.push([t, wallLength(room, side)]);
  return segs.filter(([a, b]) => b - a > 0.5);
}

// Плита вдоль стены от t0 до t1: высота h, толщина th
function wallSlab(room, side, t0, t1, h, th, mat, inset = 0) {
  const [ax, az] = wallPoint(room, side, t0, inset);
  const [bx, bz] = wallPoint(room, side, t1, inset);
  const along = side === 'north' || side === 'south';
  const m = new THREE.Mesh(new THREE.BoxGeometry(along ? t1 - t0 : th, h, along ? th : t1 - t0), mat);
  m.position.set((ax + bx) / 2, h / 2, (az + bz) / 2);
  return m;
}

export function buildRoom(scene, room, label) {
  const { w: RW, d: RD, h: RH, grid: G } = room;
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(RW, RD), new THREE.MeshStandardMaterial({ color: LIGHT }));
  floor.rotation.x = -Math.PI / 2;
  scene.add(floor);

  // Разметочная сетка 6 м по осям колонн
  const pts = [];
  for (let x = 0; x <= RW + 0.01; x += G) pts.push(new THREE.Vector3(x - RW / 2, 0.02, -RD / 2), new THREE.Vector3(x - RW / 2, 0.02, RD / 2));
  for (let y = Math.min(...room.columns.ys) % G; y <= RD + 0.01; y += G) pts.push(new THREE.Vector3(-RW / 2, 0.02, y - RD / 2), new THREE.Vector3(RW / 2, 0.02, y - RD / 2));
  scene.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: 0xc4c4c4 })));

  // Стены: внешняя — плотнее; проёмы вырезаны
  const wallMat = new THREE.MeshStandardMaterial({ color: WHITE, transparent: true, opacity: 0.55 });
  const extMat = new THREE.MeshStandardMaterial({ color: WHITE, transparent: true, opacity: 0.85 });
  for (const side of Object.keys(SIDE_RU)) {
    const ops = room.openings.filter((o) => o.wall === side).sort((a, b) => a.from - b.from);
    let t = 0;
    const mat = EXTERNAL_WALLS.includes(side) ? extMat : wallMat;
    for (const o of ops) { if (o.from > t) scene.add(wallSlab(room, side, t, o.from, RH, 0.3, mat)); t = o.to; }
    if (t < wallLength(room, side)) scene.add(wallSlab(room, side, t, wallLength(room, side), RH, 0.3, mat));
  }

  // Колонны: квадрат size×size на пересечениях осей
  const colMat = new THREE.MeshStandardMaterial({ color: GRAY });
  const s = room.columns.size;
  for (const x of room.columns.xs) for (const y of room.columns.ys) {
    const c = new THREE.Mesh(new THREE.BoxGeometry(s, RH, s), colMat);
    c.position.set(x - RW / 2, RH / 2, y - RD / 2);
    scene.add(c);
  }

  // Светопрозрачная перегородка с цехом на стене production_side (ДОПУЩЕНИЕ)
  const glassMat = new THREE.MeshPhysicalMaterial({ color: GLASS, transparent: true, opacity: 0.5, roughness: 0.05 });
  const segs = partitionSegments(room);
  for (const [t0, t1] of segs) scene.add(wallSlab(room, room.production_side, t0, t1, RH - 1, 0.1, glassMat, 0.2));
  if (segs.length) {
    const [t0, t1] = segs.reduce((a, b) => (b[1] - b[0] > a[1] - a[0] ? b : a));
    const [x, z] = wallPoint(room, room.production_side, (t0 + t1) / 2, 0.4);
    const lbl = label('Цех · вид на реальный процесс', 1.0, '#262626', 8);
    lbl.position.set(x, RH - 0.6, z);
    scene.add(lbl);
    // Рамы стекла и табличка перед ним (размеры — ДОПУЩЕНИЕ)
    const frameMat = new THREE.MeshStandardMaterial({ color: GRAY_DARK });
    for (const [a, b] of segs) for (let t = a; t <= b + 0.01; t += Math.min(3, b - a)) {
      const [fx, fz] = wallPoint(room, room.production_side, t, 0.2);
      const post = new THREE.Mesh(new THREE.BoxGeometry(0.1, RH - 1, 0.1), frameMat);
      post.position.set(fx, (RH - 1) / 2, fz);
      scene.add(post);
    }
    const inward = { north: [0, 1], south: [0, -1], west: [1, 0], east: [-1, 0] }[room.production_side];
    const [px, pz] = wallPoint(room, room.production_side, PLAQUE_T, 1.0);
    const plaque = standingPlaque('80% локализации · реестр Минпромторга', inward);
    plaque.position.set(px, 0, pz);
    scene.add(plaque);
  }

  // Проёмы: зелёные пороги и подписи
  const exitMat = new THREE.MeshStandardMaterial({ color: 0x1b9e3a, emissive: 0x0a4a1a });
  for (const o of room.openings) {
    scene.add(wallSlab(room, o.wall, o.from, o.to, 0.08, 0.6, exitMat));
    const [x, z] = wallPoint(room, o.wall, (o.from + o.to) / 2, 0.3);
    const lbl = label(`Предлагаемый ${o.role === 'entrance' ? 'вход' : 'выход'}`, 0.7, '#1b7a32', 4);
    lbl.position.set(x, 3.0, z);
    scene.add(lbl);
  }

  // Служебные помещения
  const srvMat = new THREE.MeshStandardMaterial({ color: GRAY, transparent: true, opacity: 0.45 });
  for (const a of room.service_areas || []) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(a.x1 - a.x0, 2.6, a.y1 - a.y0), srvMat);
    m.position.set((a.x0 + a.x1) / 2 - RW / 2, 1.3, (a.y0 + a.y1) / 2 - RD / 2);
    scene.add(m);
  }
}

// Вход: точка внутри зала у проёма entrance (для прогулки)
export function entrancePoint(room) {
  const o = room.openings.find((p) => p.role === 'entrance') || room.openings[0];
  return wallPoint(room, o.wall, (o.from + o.to) / 2, 1.5);
}
