import * as THREE from 'three';
import { RED, GRAY, GRAY_DARK, TEXT, RED_CSS } from './palette.js';

function canvasTexture(w, h, draw) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  t.anisotropy = 4;
  return t;
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}

// Красная непрерывная полоса в полу по ломаной pts [[x,z],…]: сегменты-плиты + диски в стыках
export function buildBeam(pts, width, y = 0.2) {
  const g = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({ color: RED, roughness: 0.5 });
  pts.forEach(([x, z], i) => {
    const joint = new THREE.Mesh(new THREE.CylinderGeometry(width / 2, width / 2, 0.02, 20), mat);
    joint.position.set(x, y, z);
    g.add(joint);
    if (!i) return;
    const [px, pz] = pts[i - 1];
    const len = Math.hypot(x - px, z - pz);
    if (len < 1e-3) return;
    const seg = new THREE.Mesh(new THREE.BoxGeometry(len, 0.02, width), mat);
    seg.position.set((x + px) / 2, y, (z + pz) / 2);
    seg.rotation.y = -Math.atan2(z - pz, x - px);
    g.add(seg);
  });
  return g;
}

// Ближайшая к точке p точка ломаной и угол сегмента, на котором она лежит (текст читается слева направо)
export function nearestOnPolyline(pts, p) {
  let best = { d: Infinity };
  for (let i = 1; i < pts.length; i++) {
    const [ax, az] = pts[i - 1], [bx, bz] = pts[i];
    const vx = bx - ax, vz = bz - az, l2 = vx * vx + vz * vz || 1;
    const t = Math.max(0, Math.min(1, ((p[0] - ax) * vx + (p[1] - az) * vz) / l2));
    const x = ax + vx * t, z = az + vz * t, d = Math.hypot(p[0] - x, p[1] - z);
    if (d < best.d) {
      let a = Math.atan2(vz, vx);
      if (a > Math.PI / 2) a -= Math.PI; else if (a < -Math.PI / 2) a += Math.PI;
      best = { d, x, z, angle: a };
    }
  }
  return best;
}

// Плашка с текстом, лежащая на полу (подпись отрезка «Луча»)
export function floorPill(text, x, z, angle, width = 4.2, height = 0.95) {
  const tex = canvasTexture(512, 116, (ctx, w, h) => {
    roundRect(ctx, 4, 4, w - 8, h - 8, 28);
    ctx.fillStyle = 'rgba(255,255,255,0.92)'; ctx.fill();
    ctx.lineWidth = 6; ctx.strokeStyle = RED_CSS; ctx.stroke();
    ctx.fillStyle = TEXT; ctx.font = 'bold 56px sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(text, w / 2, h / 2 + 3, w - 40);
  });
  const m = new THREE.Mesh(new THREE.PlaneGeometry(width, height), new THREE.MeshBasicMaterial({ map: tex, transparent: true }));
  m.rotation.x = -Math.PI / 2;
  const g = new THREE.Group();
  g.add(m);
  g.rotation.y = -angle;
  g.position.set(x, 0.24, z);
  return g;
}

// Стойка-штандарт по ДНК: серое основание, белая панель, красный рабочий акцент, вертикальная надпись названия зоны
export function buildBanner(name) {
  const g = new THREE.Group();
  const base = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.06, 0.5), new THREE.MeshStandardMaterial({ color: GRAY }));
  base.position.y = 0.03;
  const panelH = 2.0, panelW = 0.55;
  const tex = canvasTexture(128, 512, (ctx, w, h) => {
    ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = RED_CSS; ctx.fillRect(0, 0, w, 40);
    ctx.save(); ctx.translate(w / 2, h / 2 + 20); ctx.rotate(-Math.PI / 2);
    ctx.fillStyle = TEXT; ctx.font = 'bold 54px sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(name, 0, 0, h - 90);
    ctx.restore();
  });
  const panel = new THREE.Mesh(new THREE.BoxGeometry(panelW, panelH, 0.04), [
    ...Array(4).fill(new THREE.MeshStandardMaterial({ color: GRAY })),
    new THREE.MeshStandardMaterial({ map: tex }), new THREE.MeshStandardMaterial({ map: tex })]);
  panel.position.y = 0.06 + panelH / 2;
  const pole = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.2, 0.04), new THREE.MeshStandardMaterial({ color: GRAY_DARK }));
  pole.position.y = 0.06 + 0.1;
  g.add(base, pole, panel);
  return g;
}

// Табличка перед стеклом цеха, лицом в зал (inward — единичный вектор [nx, nz] внутрь зала)
export function standingPlaque(text, inward) {
  const tex = canvasTexture(640, 220, (ctx, w, h) => {
    ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = RED_CSS; ctx.fillRect(0, 0, w, 36);
    ctx.fillStyle = TEXT; ctx.font = 'bold 62px sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('80% локализации', w / 2, 100, w - 40);
    ctx.font = 'bold 44px sans-serif'; ctx.fillStyle = '#595959';
    ctx.fillText('реестр Минпромторга', w / 2, 168, w - 40);
  });
  const g = new THREE.Group();
  const board = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.83, 0.05), [
    ...Array(4).fill(new THREE.MeshStandardMaterial({ color: GRAY })),
    new THREE.MeshStandardMaterial({ map: tex }), new THREE.MeshStandardMaterial({ map: tex })]);
  board.position.y = 1.0;
  for (const dx of [-0.9, 0.9]) {
    const leg = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.6, 0.06), new THREE.MeshStandardMaterial({ color: GRAY }));
    leg.position.set(dx, 0.3, 0);
    g.add(leg);
  }
  g.add(board);
  g.rotation.y = Math.atan2(inward[0], inward[1]);
  return g;
}
