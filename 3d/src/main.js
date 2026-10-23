import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import data from './zones.json';
import { buildModel } from './models.js';

const COLORS = { red: 0xc8102e, white: 0xf2f2f2, gray: 0x8a9099 };
const { w: RW, d: RD, h: RH, grid: G } = data.room;
const $ = (id) => document.getElementById(id);

const app = $('app');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x14161a);
const camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.1, 300);
camera.position.set(0, 24, 30);
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
app.appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.maxPolarAngle = Math.PI / 2.02;

scene.add(new THREE.HemisphereLight(0xffffff, 0x333344, 1.0));
const sun = new THREE.DirectionalLight(0xffffff, 1.2);
sun.position.set(10, 30, 10);
scene.add(sun);

// Пол, сетка, стены, колонны
const floor = new THREE.Mesh(new THREE.PlaneGeometry(RW, RD), new THREE.MeshStandardMaterial({ color: 0x2a2e35 }));
floor.rotation.x = -Math.PI / 2;
scene.add(floor);
const gridPts = [];
for (let x = -RW / 2; x <= RW / 2 + 0.01; x += G) gridPts.push(new THREE.Vector3(x, 0.02, -RD / 2), new THREE.Vector3(x, 0.02, RD / 2));
for (let z = -RD / 2; z <= RD / 2 + 0.01; z += RD / 3) gridPts.push(new THREE.Vector3(-RW / 2, 0.02, z), new THREE.Vector3(RW / 2, 0.02, z));
scene.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(gridPts), new THREE.LineBasicMaterial({ color: 0x555b66 })));

const wallMat = new THREE.MeshStandardMaterial({ color: 0xdadde2, transparent: true, opacity: 0.22 });
const wall = (w, d, x, z) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, RH, d), wallMat); m.position.set(x, RH / 2, z); scene.add(m); };
wall(RW, 0.3, 0, -RD / 2); wall(RW, 0.3, 0, RD / 2); wall(0.3, RD, -RW / 2, 0); wall(0.3, RD, RW / 2, 0);

const colMat = new THREE.MeshStandardMaterial({ color: 0x9aa0aa });
for (let x = -RW / 2 + G; x < RW / 2; x += G)
  for (const z of [-RD / 2 + RD / 3, RD / 2 - RD / 3]) {
    const c = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, RH, 16), colMat);
    c.position.set(x, RH / 2, z);
    scene.add(c);
  }

// Светопрозрачная перегородка с цехом (ПРЕДПОЛОЖЕНИЕ: цех за северной стеной)
const glass = new THREE.Mesh(new THREE.BoxGeometry(RW - 6, RH - 1, 0.08),
  new THREE.MeshPhysicalMaterial({ color: 0x88ccff, transparent: true, opacity: 0.3, roughness: 0.05 }));
glass.position.set(0, (RH - 1) / 2, -RD / 2 + 0.8);
scene.add(glass);
const glassLbl = label('Светопрозрачная перегородка с цехом', 1.0, '#88ccff', 6);
glassLbl.position.set(0, RH - 0.4, -RD / 2 + 0.9);
scene.add(glassLbl);

function label(text, size, color = '#fff', aspect = 1) {
  const cv = document.createElement('canvas');
  cv.width = 128 * aspect; cv.height = 128;
  const ctx = cv.getContext('2d');
  if (aspect === 1) {
    ctx.fillStyle = '#14161a'; ctx.beginPath(); ctx.arc(64, 64, 60, 0, Math.PI * 2); ctx.fill();
  }
  ctx.fillStyle = color; ctx.font = `bold ${aspect === 1 ? 64 : 40}px sans-serif`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(text, cv.width / 2, 68);
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(cv), transparent: true }));
  sp.scale.set(size * aspect * 1.6, size * 1.6, 1);
  return sp;
}

// Зоны
const zoneMeshes = [];
const byId = {};
data.zones.forEach((z) => {
  const mat = new THREE.MeshStandardMaterial({ color: COLORS[z.kind], emissive: 0x000000 });
  const m = new THREE.Mesh(new THREE.BoxGeometry(z.w, 0.15, z.d), mat);
  m.position.set(z.x, 0.1, z.z);
  m.userData = z;
  scene.add(m);
  zoneMeshes.push(m);
  byId[z.id] = m;

  const model = buildModel(z.model);
  model.position.set(z.x, 0.18, z.z);
  scene.add(model);

  const sp = label(String(z.id), 1);
  sp.position.set(z.x, 4.3, z.z);
  scene.add(sp);
});

// Маршрут
const routePts = (ids) => ids.map((i) => { const z = data.zones[i]; return new THREE.Vector3(z.x, 0.3, z.z + (z.z > 0 ? -1.9 : 1.9)); });
let route = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: 0xffd400 }));
scene.add(route);
function setRoute(ids) { route.geometry.dispose(); route.geometry = new THREE.BufferGeometry().setFromPoints(routePts(ids)); }
const allIds = data.zones.map((z) => z.id);
setRoute(allIds);

// Сценарии
let activeScn = null;
function applyScenario(s) {
  activeScn = s;
  const ids = s ? s.zones : allIds;
  setRoute(ids);
  zoneMeshes.forEach((m) => {
    const on = ids.includes(m.userData.id);
    m.material.emissive.setHex(s && on ? 0x333300 : 0x000000);
    m.material.opacity = 1; m.material.transparent = false;
    if (s && !on) { m.material.transparent = true; m.material.opacity = 0.25; }
  });
  document.querySelectorAll('#bar-scn button').forEach((b) => b.classList.toggle('on', s && b.dataset.id === s.id));
}
const bar = $('bar-scn');
const all = document.createElement('button'); all.textContent = 'Все зоны'; all.className = 'alt'; all.onclick = () => applyScenario(null); bar.appendChild(all);
data.scenarios.forEach((s) => {
  const b = document.createElement('button'); b.textContent = s.name; b.dataset.id = s.id; b.className = 'alt'; b.onclick = () => applyScenario(s); bar.appendChild(b);
});

// Клик по зоне
const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
const card = $('card');
let downAt = null;
renderer.domElement.addEventListener('pointerdown', (e) => { downAt = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', (e) => {
  if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 5) return;
  mouse.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const hit = ray.intersectObjects(zoneMeshes)[0];
  if (!hit) { card.style.display = 'none'; return; }
  const z = hit.object.userData;
  card.innerHTML = `<h3>${z.id}. ${z.name}</h3><small>Экспонаты:</small><ul>${z.exhibits.map((x) => `<li>${x}</li>`).join('')}</ul><small>Демонстрация:</small><p style="margin:4px 0 0">${z.demo}</p>`;
  card.style.display = 'block';
});

// Режимы камеры
let mode = 'orbit';
let tour = null;
const setOn = (id) => ['btn-orbit', 'btn-top', 'btn-walk', 'btn-tour'].forEach((b) => $(b).classList.toggle('on', b === id));
function toOrbit(pos) { mode = 'orbit'; tour = null; controls.enabled = true; camera.position.set(...pos); controls.target.set(0, 0, 0); camera.up.set(0, 1, 0); $('caption').style.display = 'none'; }
$('btn-orbit').onclick = () => { toOrbit([0, 24, 30]); setOn('btn-orbit'); };
$('btn-top').onclick = () => { toOrbit([0, 45, 0.01]); setOn('btn-top'); };
$('btn-route').onclick = () => { route.visible = !route.visible; };

// Прогулка
let yaw = 0, pitch = 0, dragging = false;
const keys = {};
$('btn-walk').onclick = () => { mode = 'walk'; tour = null; controls.enabled = false; camera.position.set(-17, 1.7, 7); yaw = 0; pitch = 0; setOn('btn-walk'); };
addEventListener('keydown', (e) => { keys[e.code] = true; });
addEventListener('keyup', (e) => { keys[e.code] = false; });
renderer.domElement.addEventListener('pointerdown', () => { dragging = true; });
addEventListener('pointerup', () => { dragging = false; });
addEventListener('pointermove', (e) => { if (mode === 'walk' && dragging) { yaw -= e.movementX * 0.004; pitch = Math.max(-1.2, Math.min(1.2, pitch - e.movementY * 0.004)); } });
function walkStep(dt) {
  const f = (keys.KeyW || keys.ArrowUp ? 1 : 0) - (keys.KeyS || keys.ArrowDown ? 1 : 0);
  const s = (keys.KeyD || keys.ArrowRight ? 1 : 0) - (keys.KeyA || keys.ArrowLeft ? 1 : 0);
  const sp = 4 * dt;
  camera.position.x = Math.max(-RW / 2 + 0.5, Math.min(RW / 2 - 0.5, camera.position.x + (-Math.sin(yaw) * f + Math.cos(yaw) * s) * sp));
  camera.position.z = Math.max(-RD / 2 + 1.2, Math.min(RD / 2 - 0.5, camera.position.z + (-Math.cos(yaw) * f - Math.sin(yaw) * s) * sp));
  camera.position.y = 1.7;
  camera.rotation.set(pitch, yaw, 0, 'YXZ');
}

// Автотур по зонам 0 → 11 с подписями
function startTour() {
  mode = 'tour'; controls.enabled = false; setOn('btn-tour');
  const stops = data.zones.map((z) => ({ z, cam: new THREE.Vector3(z.x, 3.6, z.z + (z.z > 0 ? -11 : 11)), look: new THREE.Vector3(z.x, 1.0, z.z) }));
  tour = { stops, t: 0, per: 5 };
  $('caption').style.display = 'block';
}
$('btn-tour').onclick = startTour;
let tourDone = false;
function tourStep(dt) {
  tour.t += dt;
  const total = tour.stops.length * tour.per;
  if (tour.t >= total) { tourDone = true; toOrbit([0, 24, 30]); setOn('btn-orbit'); return; }
  const f = tour.t / tour.per, i = Math.min(Math.floor(f), tour.stops.length - 1), k = f - i;
  const a = tour.stops[i], b = tour.stops[Math.min(i + 1, tour.stops.length - 1)];
  const e = k * k * (3 - 2 * k);
  camera.position.lerpVectors(a.cam, b.cam, e);
  const look = new THREE.Vector3().lerpVectors(a.look, b.look, e);
  camera.lookAt(look);
  $('caption').innerHTML = `<b>${a.z.id}.</b> ${a.z.name}<br><span style="font-size:16px;color:#cfd3da">${a.z.demo}</span>`;
}
window.__tourDone = () => tourDone;
if (new URLSearchParams(location.search).get('tour') === '1') startTour();

addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });

const clock = new THREE.Clock();
(function loop() {
  const dt = Math.min(clock.getDelta(), 0.1);
  if (mode === 'walk') walkStep(dt);
  else if (mode === 'tour' && tour) tourStep(dt);
  else controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(loop);
})();
