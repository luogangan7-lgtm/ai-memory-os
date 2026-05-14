import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Stars } from '@react-three/drei';
import * as THREE from 'three';

function Particles() {
  const ref = useRef<THREE.Points>(null);
  const count = 150;
  const { pos, col } = useMemo(() => {
    const p = new Float32Array(count * 3), c = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      p[i*3]=(Math.random()-.5)*14; p[i*3+1]=(Math.random()-.5)*9; p[i*3+2]=(Math.random()-.5)*4;
      const t=Math.random()>.4; c[i*3]=t?0:.616; c[i*3+1]=t?.941:.314; c[i*3+2]=t?.831:1;
    }
    return {pos:p,col:c};
  }, []);
  useFrame((_,d)=>{if(ref.current)ref.current.rotation.y+=d*.015;});
  return (<points ref={ref}><bufferGeometry><bufferAttribute attach='attributes-position' args={[pos,3]}/><bufferAttribute attach='attributes-color' args={[col,3]}/></bufferGeometry><pointsMaterial size={.025} vertexColors transparent opacity={.5} blending={THREE.AdditiveBlending} depthWrite={false}/></points>);
}

export function NeuralBackground() {
  return (<div style={{position:'fixed',inset:0,zIndex:0,pointerEvents:'none'}}><Canvas camera={{position:[0,0,6],fov:60}} gl={{antialias:true,alpha:true}} style={{pointerEvents:'none'}}><Stars radius={40} depth={20} count={200} factor={2.5} saturation={.2} fade speed={.15}/><Particles/></Canvas></div>);
}
