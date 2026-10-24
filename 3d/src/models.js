import * as THREE from 'three';
import { RED, WHITE, GRAY, GRAY_DARK as DARK, GLASS } from './palette.js';
const mat = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.6, metalness: 0.2, ...o });
const glassMat = () => new THREE.MeshPhysicalMaterial({ color: GLASS, transparent: true, opacity: 0.28, roughness: 0.05 });

function box(w, h, d, c, x = 0, y = 0, z = 0, g) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), typeof c === 'number' ? mat(c) : c);
  m.position.set(x, y + h / 2, z);
  g.add(m);
  return m;
}
function cyl(r, h, c, x, y, z, g, rot) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, 24), typeof c === 'number' ? mat(c) : c);
  m.position.set(x, y + h / 2, z);
  if (rot) m.rotation.z = Math.PI / 2;
  g.add(m);
  return m;
}

const builders = {
  wall(g) {
    box(4.6, 3, 0.2, WHITE, 0, 0, -1.8, g);
    box(0.5, 3, 0.22, RED, -1.8, 0, -1.8, g);
    box(2.2, 0.2, 0.6, GRAY, 0, 0, 0.5, g);
    box(2.2, 1.0, 0.2, DARK, 0, 1.0, -1.6, g);
  },
  furnace(g) {
    cyl(0.9, 2.2, GRAY, 0, 0, 0, g);
    cyl(0.5, 2.6, RED, 0, 0, 0, g);
    cyl(0.15, 0.7, 0x99d6a8, 0, 2.6, 0, g);
    box(1.6, 0.9, 0.9, WHITE, 1.6, 0, 0.5, g);
  },
  quantron(g) {
    box(3.6, 0.8, 1.4, WHITE, 0, 0, 0, g);
    cyl(0.28, 2.6, RED, 0, 0.95, 0, g, true);
    const cover = new THREE.Mesh(new THREE.BoxGeometry(3.4, 1.0, 1.2), glassMat());
    cover.position.set(0, 1.3, 0);
    g.add(cover);
  },
  showcase(g) {
    for (let i = -1; i <= 1; i++) {
      box(1.2, 0.9, 0.9, WHITE, i * 1.5, 0, 0, g);
      const c = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1.1, 0.9), glassMat());
      c.position.set(i * 1.5, 1.45, 0);
      g.add(c);
      for (let k = 0; k < 3; k++) box(0.05, 0.3, 0.5, RED, i * 1.5 - 0.3 + k * 0.3, 0.9, 0, g);
    }
  },
  rack(g) {
    for (let i = -1; i <= 1; i++) {
      box(1.0, 2.0, 0.9, WHITE, i * 1.2, 0, 0, g);
      box(0.8, 0.12, 0.02, RED, i * 1.2, 1.6, 0.46, g);
      box(0.8, 0.5, 0.02, DARK, i * 1.2, 0.7, 0.46, g);
    }
  },
  optical(g) {
    box(3.6, 0.1, 1.6, GRAY, 0, 0.85, 0, g);
    for (const x of [-1.6, 1.6]) for (const z of [-0.6, 0.6]) box(0.1, 0.85, 0.1, DARK, x, 0, z, g);
    for (let i = 0; i < 6; i++) {
      box(0.1, 0.45, 0.1, DARK, -1.3 + i * 0.5, 0.95, (i % 2 ? 0.3 : -0.3), g);
      box(0.28, 0.28, 0.04, GLASS, -1.3 + i * 0.5, 1.2, (i % 2 ? 0.3 : -0.3), g);
    }
    box(1.0, 1.9, 0.9, WHITE, 2.4, 0, -1.2, g);
  },
  cutter(g) {
    box(4.0, 0.5, 2.2, GRAY, 0, 0, 0, g);
    box(4.0, 0.3, 2.2, RED, 0, 0.5, 0, g);
    const cab = new THREE.Mesh(new THREE.BoxGeometry(4.0, 1.8, 2.2), glassMat());
    cab.position.set(0, 1.7, 0);
    g.add(cab);
    box(0.3, 0.6, 0.3, RED, 0, 1.4, 0, g);
    box(1.0, 1.6, 0.8, WHITE, 2.6, 0, 0.6, g);
  },
  engraver(g) {
    box(2.4, 1.0, 1.6, WHITE, 0, 0, 0, g);
    box(2.4, 0.15, 1.6, RED, 0, 1.0, 0, g);
    box(0.3, 1.2, 0.3, GRAY, 0, 1.15, -0.5, g);
    box(0.25, 0.7, 0.25, RED, 0, 1.2, 0.1, g);
    box(1.4, 0.8, 0.8, DARK, 2.0, 0, 0.4, g);
  },
  robot(g) {
    box(3.4, 0.2, 3.0, DARK, 0, 0, 0, g);
    cyl(0.5, 0.5, WHITE, 0, 0.2, 0, g);
    box(0.35, 1.5, 0.35, RED, 0, 0.7, 0, g).rotation.z = 0.35;
    box(0.3, 1.3, 0.3, WHITE, 0.55, 1.9, 0, g).rotation.z = -0.9;
    box(0.2, 0.5, 0.2, GRAY, 1.15, 2.2, 0, g);
    const cell = new THREE.Mesh(new THREE.BoxGeometry(3.4, 2.2, 3.0), glassMat());
    cell.position.set(0, 1.3, 0);
    g.add(cell);
  },
  handheld(g) {
    box(2.8, 0.1, 1.2, WHITE, 0, 0.85, 0, g);
    for (const x of [-1.2, 1.2]) box(0.1, 0.85, 0.1, DARK, x, 0, 0, g);
    box(0.7, 0.9, 0.6, RED, -2.0, 0, -0.2, g);
    box(0.7, 0.9, 0.6, WHITE, 2.0, 0, -0.2, g);
    box(0.12, 0.12, 0.5, RED, -0.5, 0.95, 0, g);
    box(0.12, 0.12, 0.5, DARK, 0.5, 0.95, 0, g);
  },
  sampledesk(g) {
    // тест-драйв без станка: стол приёма образцов и экран результатов (обработка на зонах 6 и 7)
    box(1.6, 0.1, 0.6, WHITE, 0, 0.85, 0, g);
    for (const x of [-0.7, 0.7]) box(0.08, 0.85, 0.08, DARK, x, 0, 0, g);
    box(0.4, 0.04, 0.3, 0xc0c0c8, -0.3, 0.95, 0, g);
    box(1.2, 0.7, 0.06, DARK, 0, 1.2, -0.35, g);
    box(1.2, 0.08, 0.07, RED, 0, 1.9, -0.35, g);
  },
  'vitrine-off'(g) {
    // витрина обесточенных ручных аппаратов
    box(1.9, 0.9, 0.6, WHITE, 0, 0, 0, g);
    const c = new THREE.Mesh(new THREE.BoxGeometry(1.9, 0.9, 0.6), glassMat());
    c.position.set(0, 1.35, 0);
    g.add(c);
    box(0.5, 0.25, 0.25, GRAY, -0.5, 0.9, 0, g);
    box(0.5, 0.25, 0.25, GRAY, 0.4, 0.9, 0, g);
  },
  booth(g) {
    // закрытая кабина 3×3 м: стены, смотровое окно с лазерной защитой, вытяжка, дверь с блокировкой
    const H = 2.6, S = 3.0, T = 0.08;
    box(S, H, T, RED, 0, 0, -S / 2 + T / 2, g);
    box(T, H, S, RED, -S / 2 + T / 2, 0, 0, g);
    box(T, H, S, RED, S / 2 - T / 2, 0, 0, g);
    box(0.6, H, T, RED, -S / 2 + 0.3, 0, S / 2 - T / 2, g);
    box(1.0, H, T, DARK, S / 2 - 0.5, 0, S / 2 - T / 2, g); // дверь с блокировкой
    box(1.4, 1.0, T, RED, -0.3, 0, S / 2 - T / 2, g);
    box(1.4, 0.5, T, RED, -0.3, 2.1, S / 2 - T / 2, g);
    const win = new THREE.Mesh(new THREE.BoxGeometry(1.4, 1.1, 0.04), new THREE.MeshPhysicalMaterial({ color: 0x33aa55, transparent: true, opacity: 0.45 }));
    win.position.set(-0.3, 1.55, S / 2 - T / 2);
    g.add(win);
    box(1.6, 0.8, 1.0, WHITE, 0, 0, -0.6, g);
    cyl(0.2, 1.2, GRAY, 0.8, H, -0.9, g); // местная вытяжка
  },
  meeting(g) {
    // переговорная: стол на 10 мест, экран результатов, стеклянные стены
    box(4.0, 0.06, 1.4, WHITE, 0, 0.74, 0, g);
    box(0.2, 0.74, 0.8, GRAY, 0, 0, 0, g);
    for (let i = 0; i < 5; i++) for (const z of [-1.1, 1.1]) box(0.5, 0.45, 0.5, DARK, -1.6 + i * 0.8, 0, z, g);
    box(1.8, 1.0, 0.06, DARK, 0, 1.0, -1.85, g);
    // Открытая переговорная зона после CP2: отдельные стеклянные стены не предлагаются.
  },
  passport(g) {
    // киоск «Паспорт детали»: выдача пластины и QR-паспорта
    box(0.6, 1.1, 0.5, WHITE, 0, 0, 0, g);
    box(0.5, 0.35, 0.05, DARK, 0, 1.15, 0.1, g).rotation.x = -0.4;
    box(0.6, 0.1, 0.5, RED, 0, 1.1, 0, g);
  },
  classroom(g) {
    for (let i = 0; i < 3; i++) {
      box(1.4, 0.08, 0.7, WHITE, -1.6 + i * 1.6, 0.75, 0, g);
      box(0.06, 0.75, 0.06, GRAY, -2.2 + i * 1.6, 0, 0, g);
      box(0.06, 0.75, 0.06, GRAY, -1.0 + i * 1.6, 0, 0, g);
      box(0.6, 0.4, 0.04, DARK, -1.6 + i * 1.6, 0.83, -0.1, g);
    }
    box(1.8, 1.0, 0.1, RED, 0, 0, -1.6, g);
  },
};

export function buildModel(name) {
  const g = new THREE.Group();
  (builders[name] || builders.rack)(g);
  return g;
}
