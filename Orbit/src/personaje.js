import * as THREE from 'three';

// Ejes: X lateral, Y altura, Z profundidad. El frente mira hacia +Z.
// El origen está en el suelo entre los pies. Mantén root en (0, 0, 0).
export function crearPersonaje() {
  const root = new THREE.Group();
  root.name = 'personaje';
  const materiales = {
    principal: new THREE.MeshStandardMaterial({ color: '#ff6b6b', roughness: 0.45, metalness: 0.1 }),
    oscuro: new THREE.MeshStandardMaterial({ color: '#2d3436', roughness: 0.5 }),
    claro: new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 0.7 }),
    detalle: new THREE.MeshStandardMaterial({ color: '#feca57', roughness: 0.5 }),
    piel: new THREE.MeshStandardMaterial({ color: '#ffe0b2', roughness: 0.6 }),
  };
  // Helpers: geometría + material = malla visible; Group = conjunto transformable.
  function pieza(nombre, geometria, material, posicion, padre) {
    const malla = new THREE.Mesh(geometria, material);
    malla.name = nombre;
    malla.position.set(...posicion);
    malla.castShadow = true;
    malla.receiveShadow = true;
    padre.add(malla);
    return malla;
  }
  function grupo(nombre, posicion, padre = root) {
    const g = new THREE.Group(); g.name = nombre;
    g.position.set(...posicion); padre.add(g); return g;
  }
  // Tronco
  const torso = grupo('torso', [0, 1.72, 0]);
  pieza('cuerpo', new THREE.BoxGeometry(1.05, 1.1, 0.65), materiales.principal, [0, 0, 0], torso);

  // Pivotes de las extremidades (hombros y caderas)
  const cabeza = grupo('cabeza', [0, 2.4, 0]);
  const brazoIzquierdo = grupo('brazoIzquierdo', [-0.72, 2.08, 0]);
  const brazoDerecho = grupo('brazoDerecho', [0.72, 2.08, 0]);
  const piernaIzquierda = grupo('piernaIzquierda', [-0.3, 1.12, 0]);
  const piernaDerecha = grupo('piernaDerecha', [0.3, 1.12, 0]);

  // Cabeza con rostro (mira hacia +Z)
  pieza('cara', new THREE.BoxGeometry(0.75, 0.75, 0.75), materiales.piel, [0, 0.38, 0], cabeza);
  pieza('ojoIzquierdo', new THREE.BoxGeometry(0.14, 0.14, 0.05), materiales.oscuro, [-0.20, 0.25, 0.36], cabeza);
  pieza('ojoDerecho', new THREE.BoxGeometry(0.14, 0.14, 0.05), materiales.oscuro, [0.20, 0.25, 0.36], cabeza);
  pieza('boca', new THREE.BoxGeometry(0.25, 0.06, 0.04), materiales.oscuro, [0, 0.05, 0.35], cabeza);

  // Brazos (Y negativa desde el pivote)
  pieza('brazoIzq', new THREE.BoxGeometry(0.35, 0.95, 0.35), materiales.principal, [0, -0.48, 0], brazoIzquierdo);
  pieza('brazoDer', new THREE.BoxGeometry(0.35, 0.95, 0.35), materiales.principal, [0, -0.48, 0], brazoDerecho);
  pieza('manoIzq', new THREE.BoxGeometry(0.45, 0.25, 0.3), materiales.piel, [0, -0.98, 0], brazoIzquierdo);
  pieza('manoDer', new THREE.BoxGeometry(0.45, 0.25, 0.3), materiales.piel, [0, -0.98, 0], brazoDerecho);

  // Piernas (terminan en Y global = 0)
  pieza('piernaIzq', new THREE.BoxGeometry(0.4, 1.12, 0.4), materiales.oscuro, [0, -0.56, 0], piernaIzquierda);
  pieza('piernaDer', new THREE.BoxGeometry(0.4, 1.12, 0.4), materiales.oscuro, [0, -0.56, 0], piernaDerecha);
  pieza('pieIzq', new THREE.BoxGeometry(0.55, 0.12, 0.75), materiales.detalle, [0, -1.06, 0.2], piernaIzquierda);
  pieza('pieDer', new THREE.BoxGeometry(0.55, 0.12, 0.75), materiales.detalle, [0, -1.06, 0.2], piernaDerecha);

  return { root, partes: { torso, cabeza, brazoIzquierdo, brazoDerecho, piernaIzquierda, piernaDerecha }, materiales };
}
