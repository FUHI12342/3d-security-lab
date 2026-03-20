/**
 * targets/webgl_scene/app.js
 *
 * three.js WebGLシーン構築スクリプト。
 * - 通常メッシュ: 回転するキューブ（可視）
 * - 隠しメッシュ: scale(0,0,0) で非表示（頂点データはGPU上に存在）
 * - シェーダーuniformにフラグ文字列を埋め込み（CTF Challenge 4）
 *
 * CTF Challenge 1: 隠しメッシュの頂点数を見つけよ
 * CTF Challenge 4: シェーダーに埋め込まれた文字列を見つけよ
 */

'use strict';

// --- シーンセットアップ ---
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111122);

const camera = new THREE.PerspectiveCamera(
  60,
  window.innerWidth / window.innerHeight,
  0.1,
  100
);
camera.position.set(0, 2, 6);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.getElementById('canvas-container').appendChild(renderer.domElement);

// --- 通常メッシュ: 回転するキューブ ---
const cubeGeometry = new THREE.BoxGeometry(2, 2, 2);
const cubeMaterial = new THREE.MeshPhongMaterial({
  color: 0xff8800,
  shininess: 60,
});
const cube = new THREE.Mesh(cubeGeometry, cubeMaterial);
scene.add(cube);

// --- 隠しメッシュ: Icosphere (scale=0で非表示) ---
// CTF Challenge 1: この頂点数を見つけること
// IcosahedronGeometry(1, 1) → 80 三角形面 → 240 頂点 (indexed) / 80*3=240 non-indexed
const hiddenGeometry = new THREE.IcosahedronGeometry(1.5, 1);
const hiddenMaterial = new THREE.MeshBasicMaterial({
  color: 0x00ff88,
  wireframe: true,
});
const hiddenMesh = new THREE.Mesh(hiddenGeometry, hiddenMaterial);
// スケールを0にして非表示にする（ただしドローコールは発行される）
hiddenMesh.scale.set(0, 0, 0);
hiddenMesh.position.set(0, 0, 0);
scene.add(hiddenMesh);

// --- カスタムシェーダーマテリアル（CTF Challenge 4） ---
// uniformに隠された文字列が埋め込まれている
const secretShaderMaterial = new THREE.ShaderMaterial({
  uniforms: {
    u_time: { value: 0.0 },
    // シェーダーシークレット (CTF Challenge 4の答え)
    u_secret: { value: 'FLAG{shader_secret_Xk9mP2rQ}' },
    u_color: { value: new THREE.Color(0x4488ff) },
  },
  vertexShader: `
    uniform float u_time;
    varying vec2 vUv;
    void main() {
      vUv = uv;
      vec3 pos = position;
      pos.y += sin(pos.x * 2.0 + u_time) * 0.1;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `,
  fragmentShader: `
    // u_secret: FLAG{shader_secret_Xk9mP2rQ}
    uniform vec3 u_color;
    uniform float u_time;
    varying vec2 vUv;
    void main() {
      float wave = sin(vUv.x * 10.0 + u_time) * 0.5 + 0.5;
      gl_FragColor = vec4(u_color * wave, 1.0);
    }
  `,
});

// シェーダーマテリアルを使った平面
const planeGeometry = new THREE.PlaneGeometry(4, 4, 8, 8);
const plane = new THREE.Mesh(planeGeometry, secretShaderMaterial);
plane.rotation.x = -Math.PI / 2;
plane.position.y = -2;
scene.add(plane);

// --- ライティング ---
const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
scene.add(ambientLight);

const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(5, 10, 5);
scene.add(dirLight);

// --- アニメーションループ ---
let frameCount = 0;

function animate() {
  requestAnimationFrame(animate);

  const t = frameCount * 0.016;
  cube.rotation.y = t * 0.5;
  cube.rotation.x = t * 0.3;

  secretShaderMaterial.uniforms.u_time.value = t;

  renderer.render(scene, camera);
  frameCount++;
}

// --- ウィンドウリサイズ対応 ---
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// デバッグ情報をコンソールに出力
console.log('[3D Security Lab] WebGL Scene Loaded');
console.log('[Info] Scene objects:', scene.children.length);
console.log('[Info] Hidden mesh vertex count:', hiddenGeometry.attributes.position.count);
console.log('[Hint] Use Spector.js to capture WebGL commands and find the hidden mesh!');

animate();
