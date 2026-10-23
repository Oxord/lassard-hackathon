import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import data from './zones.json';

const COLORS = { red: 0xc8102e, white: 0xf2f2f2, gray: 0x8a9099 };
const { w: RW, d: RD, h: RH, grid: G } = data.room;

const app = document.getElementById('app');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x14161a);
const camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.1, 300);
camera.position.set(0, 24, 30);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
app.appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0, 0);
controls.maxPolarAngle = Math.PI / 2.02;

scene.add(new THREE.HemisphereLight(0xffffff, 0x333344, 1.0));
const sun = new THREE.DirectionalLight(0xffffff, 1.2);
sun.position.set(10, 30, 10);
scene.add(sun);

// Пол и сетка 6x6
const floor = new THREE.Mesh(new THREE.PlaneGeometry(RW, RD), new THREE.MeshStandardMaterial({ color: 0x2a2e35 }));
floor.rotation.x = -Math.PI / 2;
scene.add(floor);
const gridPts = [];
for (let x = -RW / 2; x <= RW / 2 + 0.01; x += G) gridPts.push(new THREE.Vector3(x, 0.02, -RD / 2), new THREE.Vector3(x, 0.02, RD / 2));
for (let z = -RD / 2; z <= RD / 2 + 0.01; z += RD / 3) gridPts.push(new THREE.Vector3(-RW / 2, 0.02, z), new THREE.Vector3(RW / 2, 0.02, z));
const grid = new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(gridPts), new THREE.LineBasicMaterial({ color: 0x555b66 }));
scene.add(grid);

// Стены (4 внешние, низкая прозрачность чтобы видеть внутрь)
const wallMat = new THREE.MeshStandardMaterial({ color: 0xdadde2, transparent: true, opacity: 0.25 });
function wall(w, d, x, z) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, RH, d), wallMat);
  m.position.set(x, RH / 2, z);
  scene.add(m);
}
wall(RW, 0.3, 0, -RD / 2);
wall(RW, 0.3, 0, RD / 2);
wall(0.3, RD, -RW / 2, 0);
wall(0.3, RD, RW / 2, 0);

// Колонны по сетке 6x6
const colMat = new THREE.MeshStandardMaterial({ color: 0x9aa0aa });
for (let x = -RW / 2 + G; x < RW / 2; x += G) {
  for (const z of [-RD / 2 + RD / 3, RD / 2 - RD / 3]) {
    const c = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, RH, 16), colMat);
    c.position.set(x, RH / 2, z);
    scene.add(c);
  }
}

// Светопрозрачная перегородка вдоль северной стены (ПРЕДПОЛОЖЕНИЕ: цех с северной стороны)
const glass = new THREE.Mesh(
  new THREE.BoxGeometry(RW - 6, RH - 1, 0.08),
  new THREE.MeshPhysicalMaterial({ color: 0x88ccff, transparent: true, opacity: 0.3, roughness: 0.05 })
);
glass.position.set(0, (RH - 1) / 2, -RD / 2 + 0.8);
scene.add(glass);

// Зоны
const zoneMeshes = [];
const labels = [];
data.zones.forEach((z) => {
  const mat = new THREE.MeshStandardMaterial({ color: COLORS[z.kind], emissive: 0x000000 });
  const m = new THREE.Mesh(new THREE.BoxGeometry(z.w, 0.15, z.d), mat);
  m.position.set(z.x, 0.1, z.z);
  m.userData = z;
  scene.add(m);
  zoneMeshes.push(m);

  // Заглушка экспоната: блок по центру зоны (R3 заменяет на модель, задача C1)
  const ex = new THREE.Mesh(
    new THREE.BoxGeometry(z.w * 0.4, 1.6, z.d * 0.4),
    new THREE.MeshStandardMaterial({ color: z.kind === 'red' ? 0x555b66 : 0xc8102e })
  );
  ex.position.set(z.x, 0.95, z.z);
  scene.add(ex);

  // Номер зоны
  const cv = document.createElement('canvas');
  cv.width = cv.height = 128;
  const ctx = cv.getContext('2d');
  ctx.fillStyle = '#14161a';
  ctx.beginPath(); ctx.arc(64, 64, 60, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#fff'; ctx.font = 'bold 64px sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(String(z.id), 64, 68);
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(cv) }));
  sp.scale.set(1.6, 1.6, 1);
  sp.position.set(z.x, 3, z.z);
  scene.add(sp);
  labels.push(sp);
});

// Маршрут 0 → 11
const routePts = data.zones.map((z) => new THREE.Vector3(z.x, 0.3, z.z + (z.z > 0 ? -1.8 : 1.8)));
const route = new THREE.Line(
  new THREE.BufferGeometry().setFromPoints(routePts),
  new THREE.LineBasicMaterial({ color: 0xffd400 })
);
scene.add(route);

// Клик по зоне
const ray = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const card = document.getElementById('card');
let selected = null;
renderer.domElement.addEventListener('pointerdown', (e) => {
  mouse.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const hit = ray.intersectObjects(zoneMeshes)[0];
  if (selected) selected.material.emissive.setHex(0x000000);
  if (!hit) { card.style.display = 'none'; selected = null; return; }
  selected = hit.object;
  selected.material.emissive.setHex(0x553300);
  const z = selected.userData;
  card.innerHTML = `<h3>${z.id}. ${z.name}</h3><small>Экспонаты:</small><ul>${z.exhibits.map((x) => `<li>${x}</li>`).join('')}</ul>`;
  card.style.display = 'block';
});

// Кнопки
document.getElementById('btn-orbit').onclick = () => { camera.position.set(0, 24, 30); controls.target.set(0, 0, 0); };
document.getElementById('btn-top').onclick = () => { camera.position.set(0, 45, 0.01); controls.target.set(0, 0, 0); };
document.getElementById('btn-route').onclick = () => { route.visible = !route.visible; };

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

(function loop() {
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(loop);
})();
