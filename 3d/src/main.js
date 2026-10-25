import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import data from './zones.json';
import routes from './routes.json';
import { buildModel } from './models.js';
import { buildRoom, entrancePoint } from './room.js';
import { createLabels } from './labels.js';
import { RED, GRAY, WHITE, BEAM_WIDTH } from './palette.js';
import { buildBeam, buildBanner, floorPill } from './decals.js';
import { placeFloorPills } from './placement.js';

const COLORS = { red: RED, white: WHITE, gray: GRAY };
const { w: RW, d: RD } = data.room;
const $ = (id) => document.getElementById(id);

const app = $('app');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xf4f4f4);
const camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.1, 300);
camera.position.set(0, 24, 30);
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
app.appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.maxPolarAngle = Math.PI / 2.02;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.8;
let autoRotateWanted = true;

scene.add(new THREE.HemisphereLight(0xffffff, 0xbdbdbd, 1.6));
const sun = new THREE.DirectionalLight(0xffffff, 1.2);
sun.position.set(10, 30, 10);
scene.add(sun);

// Зал: пол, разметка 6 м, стены с проёмами, колонны 12 м, перегородка с цехом — из параметров room
const labels = createLabels();
const label = labels.create;
buildRoom(scene, data.room, label);

// Зоны
const zoneMeshes = [];
const byId = {};
const zoneExtras = {};
data.zones.forEach((z) => {
  const mat = new THREE.MeshStandardMaterial({ color: COLORS[z.kind], emissive: 0x000000 });
  const m = new THREE.Mesh(new THREE.BoxGeometry(z.w, 0.15, z.d), mat);
  m.position.set(z.x, 0.1, z.z);
  m.userData = z;
  scene.add(m);
  zoneMeshes.push(m);
  byId[z.id] = m;

  const model = fitModel(buildModel(z.model), z);
  if (z.model === 'booth' && z.front === 'N') model.rotation.y += Math.PI;
  model.position.set(z.x, 0.18, z.z);
  scene.add(model);

  const banner = buildBanner(z.name);
  const [bx, bz] = bannerSpot(z);
  banner.position.set(bx, 0.17, bz);
  scene.add(banner);

  zoneExtras[z.id] = { model, banner };

  const sp = label(String(z.id), 1);
  sp.position.set(z.x, 4.3, z.z);
  scene.add(sp);
});

// Затемнение зон вне сценария: красим модель и штендер в серый (устойчиво к стопке
// полупрозрачных поверхностей моделей — при наложении через opacity плотные модели
// из многих боксов визуально почти не бледнеют, слои альфа-блендинга складываются обратно в насыщенный цвет)
const GRAY_OUT = new THREE.Color(0xb0b0b0);
function setZoneDimmed(root, dimmed) {
  root.traverse((obj) => {
    if (!obj.isMesh) return;
    const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
    mats.forEach((mt) => {
      if (!mt.color) return;
      if (mt.userData.baseColorHex === undefined) { mt.userData.baseColorHex = mt.color.getHex(); mt.userData.baseOpacity = mt.opacity; mt.userData.baseTransparent = mt.transparent; }
      if (dimmed) {
        mt.color.setHex(mt.userData.baseColorHex).lerp(GRAY_OUT, 0.8);
        mt.opacity = mt.userData.baseOpacity * 0.55; mt.transparent = true;
      } else {
        mt.color.setHex(mt.userData.baseColorHex);
        mt.opacity = mt.userData.baseOpacity; mt.transparent = mt.userData.baseTransparent;
      }
    });
  });
}

// Стойка-штандарт: у переднего угла зоны (front — сторона подхода), внутри полосы обслуживания
function bannerSpot(z) {
  const [fx, fz] = { N: [0, -1], S: [0, 1], W: [-1, 0], E: [1, 0] }[z.front] || [0, 1];
  return fx ? [z.x + fx * (z.w / 2 - 0.3), z.z - z.d / 2 + 0.35] : [z.x - z.w / 2 + 0.35, z.z + fz * (z.d / 2 - 0.3)];
}

// Модель вписываем в габарит зоны: поворот на 90°, если длинные стороны не совпадают, и уменьшение до зоны
function fitModel(model, z) {
  const size = new THREE.Box3().setFromObject(model).getSize(new THREE.Vector3());
  if ((size.x > size.z) !== (z.w > z.d) && Math.abs(size.x - size.z) > 0.3) { model.rotation.y = Math.PI / 2; [size.x, size.z] = [size.z, size.x]; }
  const k = Math.min(1, (z.w - 0.2) / size.x, (z.d - 0.2) / size.z);
  model.scale.setScalar(k);
  return model;
}

// Маршруты ролей: тонкий серый пунктир по проходам из routes.json (генерирует plan/make_plan.py)
let route = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineDashedMaterial({ color: GRAY, dashSize: 0.35, gapSize: 0.25 }));
scene.add(route);
function setRoute(key) {
  const pts = (routes.routes[key] || routes.routes.all).map(([x, z]) => new THREE.Vector3(x, 0.26, z));
  route.geometry.dispose();
  route.geometry = new THREE.BufferGeometry().setFromPoints(pts);
  route.computeLineDistances();
}

// «Луч ЛАССАРД»: непрерывная красная полоса от стены истории через зоны 1–10 к стеклу цеха.
// Ломаная — участок основного маршрута all от остановки 0 до остановки 10, далее по свободному проходу к стеклу (ДОПУЩЕНИЕ).
const BEAM_GLASS_X = -3.4, BEAM_GLASS_Z = 7.75;
function beamPoints() {
  const all = routes.routes.all;
  const near = (p) => all.reduce((bi, q, i) => (Math.hypot(q[0] - p[0], q[1] - p[1]) < Math.hypot(all[bi][0] - p[0], all[bi][1] - p[1]) ? i : bi), 0);
  const from = near(routes.stops['0']), to = near(routes.stops['10']);
  const lane = all[from + 1] ? all.slice(from, to + 1) : all;
  const back = lane[lane.length - 1];
  return [...lane, [back[0], 2.45], [BEAM_GLASS_X, 2.45], [BEAM_GLASS_X, BEAM_GLASS_Z]];
}
const beam = beamPoints();
scene.add(buildBeam(beam, BEAM_WIDTH));
// Подписи отрезков: Обнинск — зоны 1, 2, 3, 5; Варшавка — 4; Технополис — 6–10 (ДОПУЩЕНИЕ: места подписей)
const SEGMENTS = [['Обнинск', [1, 2, 3, 5]], ['Варшавка', [4]], ['Технополис', [6, 7, 8, 9, 10]]];
const pillZones = SEGMENTS.flatMap(([name, ids]) => ids.map((id) => ({ name, id })));
const pillSpots = placeFloorPills(beam, pillZones.map(({ id }) => routes.stops[String(id)]), data.zones, data.room, data.zones.map(bannerSpot));
pillZones.forEach(({ name }, i) => scene.add(floorPill(name, pillSpots[i].x, pillSpots[i].z, pillSpots[i].angle)));
const allIds = data.zones.map((z) => z.id);
setRoute('all');

// Сценарии
let activeScn = null;
function applyScenario(s) {
  activeScn = s;
  const ids = s ? s.zones : allIds;
  setRoute(s ? s.id : 'all');
  zoneMeshes.forEach((m) => {
    const on = ids.includes(m.userData.id);
    const dimmed = Boolean(s) && !on;
    m.material.emissive.setHex(s && on ? 0x330000 : 0x000000);
    setZoneDimmed(m, dimmed);
    const extra = zoneExtras[m.userData.id];
    setZoneDimmed(extra.model, dimmed);
    setZoneDimmed(extra.banner, dimmed);
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
  card.innerHTML = `<h3>${z.id}. ${z.name}</h3><small>Экспонаты:</small><ul>${z.exhibits.map((x) => `<li>${x}</li>`).join('')}</ul><small>Демонстрация:</small><p style="margin:4px 0 0">${z.demo}</p><small>Зона ${z.w}×${z.d} м; габарит ${z.dims.equip.join('×')} м — ${z.dims.status === 'DIM_TBD' ? 'DIM_TBD, допущение' : 'по facts.md'}</small>`;
  card.style.display = 'block';
});

// Режимы камеры
let mode = 'orbit';
let tour = null;
const setOn = (id) => ['btn-orbit', 'btn-top', 'btn-walk', 'btn-tour'].forEach((b) => $(b).classList.toggle('on', b === id));
function toOrbit(pos, autoRotate) {
  mode = 'orbit'; tour = null; controls.enabled = true;
  camera.position.set(...pos); controls.target.set(0, 0, 0); camera.up.set(0, 1, 0);
  $('caption').style.display = 'none';
  autoRotateWanted = autoRotate; controls.autoRotate = autoRotate;
}
$('btn-orbit').onclick = () => { toOrbit([0, 24, 30], true); setOn('btn-orbit'); };
$('btn-top').onclick = () => { toOrbit([0, 45, 0.01], false); setOn('btn-top'); };
$('btn-route').onclick = () => { route.visible = !route.visible; };
// Автовращение «Облёта» приостанавливается, пока дом крутит сцену мышью, и возобновляется после отпускания
renderer.domElement.addEventListener('pointerdown', () => { controls.autoRotate = false; });
addEventListener('pointerup', () => { if (mode === 'orbit') controls.autoRotate = autoRotateWanted; });

// Прогулка
let yaw = 0, pitch = 0, dragging = false;
const keys = {};
$('btn-walk').onclick = () => { mode = 'walk'; tour = null; controls.enabled = false; const [ex, ez] = entrancePoint(data.room); camera.position.set(ex, 1.7, ez); yaw = 0; pitch = 0; setOn('btn-walk'); };
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

// Автотур: вступление, зоны по кольцу маршрута (route_order) с подписями, стекло цеха, финал
const PER = 4;
const TRANSITION = 1.3; // переход между остановками, с; остальное время сегмента — кадр стоит
const easeInOutCubic = (t) => (t < 0.5 ? 4 * t * t * t : 1 - ((-2 * t + 2) ** 3) / 2);
const FRONT = { N: [0, -1], S: [0, 1], W: [-1, 0], E: [1, 0] };
function makeStops() {
  const zoneById = Object.fromEntries(data.zones.map((z) => [z.id, z]));
  const zs = data.route_order.map((id) => {
    const z = zoneById[id];
    const [nx, nz] = FRONT[z.front] || [0, 1];
    return {
      title: `<b>${z.id}.</b> ${z.name}`, sub: z.demo,
      cam: new THREE.Vector3(z.x + nx * 8, 4.4, z.z + nz * 8), look: new THREE.Vector3(z.x, 0.9, z.z),
    };
  });
  const [fx, fz] = routes.finale;
  const [nx, nz] = { north: [0, -1], south: [0, 1], west: [-1, 0], east: [1, 0] }[data.room.production_side];
  const glass = {
    title: '<b>Вид на цех</b>', sub: 'Цех снизу схемы по CP2. Перегородка и защитное исполнение предлагаются и требуют согласования',
    cam: new THREE.Vector3(fx - nx * 4, 3.2, fz - nz * 4), look: new THREE.Vector3(fx + nx * 3, 2.0, fz + nz * 3),
  };
  zs.splice(zs.length - 1, 0, glass);
  const intro = { title: '<b>Трио · ЛАССАРД</b>: «Путь станка»', sub: 'Концепция шоурума: компоненты, компактное оборудование и задача посетителя', cam: new THREE.Vector3(0, 22, 27), look: new THREE.Vector3(0, 0, 0) };
  const outro = { title: 'Понять процесс. Сравнить результат. Обсудить задачу', sub: 'Концепция после CP2 · планировка и защитные решения требуют согласования', cam: new THREE.Vector3(0, 30, 3), look: new THREE.Vector3(0, 0, 0) };
  return [intro, ...zs, outro];
}
function startTour() {
  mode = 'tour'; controls.enabled = false; setOn('btn-tour');
  tour = { stops: makeStops(), t: 0, per: PER };
  $('caption').style.display = 'block';
}
$('btn-tour').onclick = startTour;
let tourDone = false;
function tourStep(dt) {
  tour.t += dt;
  const total = tour.stops.length * tour.per;
  if (tour.t >= total) { tourDone = true; toOrbit([0, 24, 30]); setOn('btn-orbit'); return; }
  const f = tour.t / tour.per, i = Math.min(Math.floor(f), tour.stops.length - 1), k = f - i;
  const a = tour.stops[Math.max(i - 1, 0)], b = tour.stops[i];
  const e = easeInOutCubic(Math.min(1, k * tour.per / TRANSITION));
  camera.position.lerpVectors(a.cam, b.cam, e);
  camera.lookAt(new THREE.Vector3().lerpVectors(a.look, b.look, e));
  $('caption').innerHTML = `${b.title}<br><span style="font-size:16px;color:#595959">${b.sub}</span>`;
}
window.__tourDone = () => tourDone;
// Для записи видео: кадр на заданной секунде (Playwright вызывает window.__renderAt(t))
window.__tourLength = () => makeStops().length * PER;
window.__renderAt = (t) => {
  window.__frozen = true;
  if (!tour) startTour();
  mode = 'tour'; tour.t = Math.min(t, makeStops().length * PER - 0.001);
  tourStep(0);
  labels.update(camera, innerWidth, innerHeight, true);
  renderer.render(scene, camera);
};
const qs = new URLSearchParams(location.search);
if (qs.get('clean') === '1') ['bar-top', 'bar-scn', 'hint'].forEach((id) => { $(id).style.display = 'none'; });
if (qs.get('tour') === '1') startTour();

addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });

const clock = new THREE.Clock();
(function loop() {
  const dt = Math.min(clock.getDelta(), 0.1);
  if (mode === 'walk') walkStep(dt);
  else if (mode === 'tour' && tour) { if (!window.__frozen) tourStep(dt); }
  else controls.update();
  labels.update(camera, innerWidth, innerHeight, mode === 'walk' || mode === 'tour');
  renderer.render(scene, camera);
  requestAnimationFrame(loop);
})();
