import * as THREE from 'three';

// Размеры ограничены пикселями экрана, чтобы приближение не раздувало подписи.
export function createLabels() {
  const labels = [];
  const point = new THREE.Vector3();
  const viewPoint = new THREE.Vector3();
  const projected = new THREE.Vector3();

  function create(text, size, color = '#262626', aspect = 1) {
    const canvas = document.createElement('canvas');
    canvas.width = 128 * aspect;
    canvas.height = 128;
    const context = canvas.getContext('2d');
    if (aspect === 1) {
      context.fillStyle = '#ffffff';
      context.beginPath();
      context.arc(64, 64, 58, 0, Math.PI * 2);
      context.fill();
      context.lineWidth = 7;
      context.strokeStyle = '#dd191c';
      context.stroke();
    } else {
      context.fillStyle = 'rgba(255,255,255,0.88)';
      context.fillRect(0, 22, canvas.width, 92);
    }
    context.fillStyle = color;
    context.font = `bold ${aspect === 1 ? 64 : 40}px sans-serif`;
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(text, canvas.width / 2, 68);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
      map: new THREE.CanvasTexture(canvas), transparent: true,
    }));
    const height = size * 1.6;
    sprite.scale.set(height * aspect, height, 1);
    labels.push({ sprite, height, aspect });
    return sprite;
  }

  function update(camera, width, height, hidden = false) {
    camera.updateMatrixWorld();
    const candidates = [];
    const pixelsPerDepth = height / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))) * camera.zoom;
    for (const entry of labels) {
      const { sprite, aspect } = entry;
      sprite.visible = false;
      if (hidden) continue;
      sprite.getWorldPosition(point);
      const depth = -viewPoint.copy(point).applyMatrix4(camera.matrixWorldInverse).z;
      if (depth <= camera.near || depth >= camera.far) continue;
      projected.copy(point).project(camera);
      if (projected.z < -1 || projected.z > 1) continue;
      const limit = Math.min(aspect === 1 ? 32 : 48, Math.max(0, width - 24) / aspect);
      const worldHeight = Math.min(entry.height, limit * depth / pixelsPerDepth);
      sprite.scale.set(worldHeight * aspect, worldHeight, 1);
      const h = worldHeight * pixelsPerDepth / depth;
      const w = h * aspect;
      const x = (projected.x + 1) * width / 2;
      const y = (1 - projected.y) * height / 2;
      const rect = { left: x - w / 2, right: x + w / 2, top: y - h / 2, bottom: y + h / 2 };
      if (rect.left < 12 || rect.right > width - 12 || rect.top < 12 || rect.bottom > height - 12) continue;
      candidates.push({ sprite, rect, depth, isZone: aspect === 1 });
    }
    // При пересечении оставляем ближайший номер зоны, затем общие подписи зала.
    candidates.sort((a, b) => Number(b.isZone) - Number(a.isZone) || a.depth - b.depth);
    const accepted = [];
    for (const { sprite, rect } of candidates) {
      if (accepted.some((other) => rect.left < other.right + 4 && rect.right > other.left - 4
        && rect.top < other.bottom + 4 && rect.bottom > other.top - 4)) continue;
      sprite.visible = true;
      accepted.push(rect);
    }
  }

  return { create, update };
}
