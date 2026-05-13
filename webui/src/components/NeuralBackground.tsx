import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import * as THREE from 'three';

function NeuralParticles() {
  const meshRef = useRef<THREE.Points>(null);
  const count = 180;
  const { positions, colors } = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const col = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 14;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 9;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 4;
      const isTeal = Math.random() > 0.4;
      col[i * 3] = isTeal ? 0 : 0.616;    // teal=0, violet=0.616
      col[i * 3 + 1] = isTeal ? 0.941 : 0.314; // teal=0.941, violet=0.314
      col[i * 3 + 2] = isTeal ? 0.831 : 1.0;   // teal=0.831, violet=1.0
    }
    return { positions: pos, colors: col };
  }, []);

  useFrame((_, delta) => {
    if (meshRef.current) meshRef.current.rotation.y += delta * 0.02;
  });

  return (
    <points ref={meshRef}>
      <bufferGeometry>
        <bufferAttribute attach='attributes-position' args={[positions, 3]} />
        <bufferAttribute attach='attributes-color' args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial size={0.025} vertexColors transparent opacity={0.55} blending={THREE.AdditiveBlending} depthWrite={false} />
    </points>
  );
}

export function NeuralBackground() {
  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none' }}>
      <Canvas
        camera={{ position: [0, 0, 6], fov: 60, near: 0.1, far: 2000 }}
        gl={{ antialias: true, alpha: true }}
        style={{ pointerEvents: 'none' }}
      >
        <ambientLight intensity={0.05} />
        <Stars radius={40} depth={20} count={200} factor={2.5} saturation={0.2} fade speed={0.2} />
        <NeuralParticles />
      </Canvas>
    </div>
  );
}
