import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { crearPersonaje } from './personaje.js';
import './style.css';

const visor = document.querySelector('#visor');
const estado = document.querySelector('#estado');
try {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#edf2f0');
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  visor.appendChild(renderer.domElement);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.minDistance = 3;
  controls.maxDistance = 14;
  controls.maxPolarAngle = Math.PI / 2 - 0.03;
  scene.add(new THREE.HemisphereLight('#ffffff', '#879d89', 2.5));
  const luz = new THREE.DirectionalLight('#fff5df', 4);
  luz.position.set(4, 7, 5);
  luz.castShadow = true;
  luz.shadow.mapSize.set(2048, 2048);
  Object.assign(luz.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6 });
  luz.shadow.normalBias = 0.03;
  scene.add(luz);
  const suelo = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.MeshStandardMaterial({ color: '#e3ece5', roughness: 1 }));
  suelo.rotation.x = -Math.PI / 2;
  suelo.receiveShadow = true;
  scene.add(suelo);
  const personaje = crearPersonaje();
  scene.add(personaje.root);

  // La escena consume este contrato en ambas versiones.
  // En la siguiente entrega se conectarán aquí las animaciones y controles.
  function vista(tipo) {
    personaje.root.rotation.y = 0;
    document.querySelector('#girar').checked = false;
    controls.autoRotate = false;
    controls.target.set(0, 1.55, 0);
    const puntos = { front: [0, 2.8, 7.7], side: [7.7, 2.8, 0], back: [0, 2.8, -7.7], home: [5, 3.6, 6] };
    camera.position.set(...puntos[tipo]);
    controls.update();
  }
  document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => vista(b.dataset.view)));
  document.querySelector('#girar').addEventListener('change', e => { controls.autoRotate = e.target.checked; controls.autoRotateSpeed = 1.4; });
  document.querySelector('#color').value = '#' + personaje.materiales.principal.color.getHexString();
  document.querySelector('#color').addEventListener('input', e => personaje.materiales.principal.color.set(e.target.value));
  document.querySelector('#captura').addEventListener('click', () => {
    renderer.render(scene, camera);
    renderer.domElement.toBlob(blob => {
      if (!blob) { estado.textContent = 'No se pudo generar la imagen.'; return; }
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'mi-personaje.png'; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      estado.textContent = 'Imagen guardada.';
    }, 'image/png');
  });
  new ResizeObserver(() => {
    const { width, height } = visor.getBoundingClientRect();
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }).observe(visor);
  vista('home');
  renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
  estado.textContent = 'Listo para explorar';
} catch (error) {
  console.error(error);
  estado.textContent = 'No se pudo iniciar el visor. Revisa la consola y que WebGL esté habilitado.';
}
