import { useEffect, useRef } from 'react';
import { Box } from '@chakra-ui/react';

export type OrbState = 'idle' | 'listening' | 'thinking' | 'speaking';

export interface OrbVisualProps {
  /** Pixel size, or a CSS length ('100%') to fill a parent that controls the actual size. */
  size?: number | string;
  /** Reactive look, matching the voice agent's own orb (voice-agent/ui/orb.html). */
  state?: OrbState;
}

// ---------------------------------------------------------------------------
// Geometry: an "evolving neural BIM core" -- a rotating geodesic wireframe
// (structural nodes + blueprint-line edges), NOT a smooth particle globe.
// Built once at module load; a subdivided icosahedron gives the faceted,
// engineered look a planet-style point-cloud doesn't.
// ---------------------------------------------------------------------------

interface Vec3 {
  x: number;
  y: number;
  z: number;
}

function normalize([x, y, z]: [number, number, number]): Vec3 {
  const len = Math.hypot(x, y, z) || 1;
  return { x: x / len, y: y / len, z: z / len };
}

function buildIcosahedron(): { vertices: Vec3[]; faces: Array<[number, number, number]> } {
  const phi = (1 + Math.sqrt(5)) / 2;
  const raw: Array<[number, number, number]> = [
    [-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
    [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
    [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1],
  ];
  const faces: Array<[number, number, number]> = [
    [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
    [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
    [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
    [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
  ];
  return { vertices: raw.map(normalize), faces };
}

/** One level of geodesic subdivision -- each triangle becomes 4, midpoints re-projected onto the unit sphere. */
function subdivide(
  vertices: Vec3[],
  faces: Array<[number, number, number]>,
): { vertices: Vec3[]; faces: Array<[number, number, number]> } {
  const nextVertices = vertices.slice();
  const midpointCache = new Map<string, number>();

  function midpoint(a: number, b: number): number {
    const key = a < b ? `${a}_${b}` : `${b}_${a}`;
    const cached = midpointCache.get(key);
    if (cached !== undefined) return cached;
    const va = nextVertices[a];
    const vb = nextVertices[b];
    const mid = normalize([(va.x + vb.x) / 2, (va.y + vb.y) / 2, (va.z + vb.z) / 2]);
    const index = nextVertices.push(mid) - 1;
    midpointCache.set(key, index);
    return index;
  }

  const nextFaces: Array<[number, number, number]> = [];
  for (const [a, b, c] of faces) {
    const ab = midpoint(a, b);
    const bc = midpoint(b, c);
    const ca = midpoint(c, a);
    nextFaces.push([a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]);
  }
  return { vertices: nextVertices, faces: nextFaces };
}

function edgesFromFaces(faces: Array<[number, number, number]>): Array<[number, number]> {
  const seen = new Set<string>();
  const edges: Array<[number, number]> = [];
  for (const [a, b, c] of faces) {
    for (const [x, y] of [[a, b], [b, c], [c, a]] as Array<[number, number]>) {
      const key = x < y ? `${x}_${y}` : `${y}_${x}`;
      if (seen.has(key)) continue;
      seen.add(key);
      edges.push([x, y]);
    }
  }
  return edges;
}

const HUB_VERTEX_COUNT = 12; // the original icosahedron vertices, before subdivision -- drawn as bigger "structural" nodes
const base = buildIcosahedron();
const CORE = subdivide(base.vertices, base.faces);
const CORE_VERTICES = CORE.vertices;
const CORE_EDGES = edgesFromFaces(CORE.faces);

interface NeuralLink {
  a: number;
  b: number;
  phase: number;
  speed: number;
}

// A sparser secondary layer: connections between NON-adjacent nodes that
// fade in and out over time -- the "evolving neural" read layered on top
// of the rigid structural wireframe above.
const structuralEdgeKeys = new Set(CORE_EDGES.map(([a, b]) => (a < b ? `${a}_${b}` : `${b}_${a}`)));
const NEURAL_LINKS: NeuralLink[] = (() => {
  const links: NeuralLink[] = [];
  for (let i = 0; i < CORE_VERTICES.length && links.length < 26; i += 3) {
    const a = i;
    const b = (i + 7) % CORE_VERTICES.length;
    if (a === b) continue;
    const key = a < b ? `${a}_${b}` : `${b}_${a}`;
    if (structuralEdgeKeys.has(key)) continue;
    const va = CORE_VERTICES[a];
    const vb = CORE_VERTICES[b];
    const dist = Math.hypot(va.x - vb.x, va.y - vb.y, va.z - vb.z);
    if (dist > 0.9) continue; // only nearby-ish nodes read as a plausible link
    links.push({ a, b, phase: Math.random() * Math.PI * 2, speed: 0.4 + Math.random() * 0.6 });
  }
  return links;
})();

// A handful of structural edges carry a travelling "data pulse" -- the
// blueprint literally animating rather than sitting static.
const PULSE_EDGES = CORE_EDGES.filter((_, i) => i % 5 === 0).map((edge, i) => ({
  edge,
  phase: (i * 0.37) % 1,
  speed: 0.18 + (i % 4) * 0.05,
}));

/** A flat NxN reference grid (like an architectural floor-plan gridline set) spanning [-size,size] on one plane. */
function buildGridPlane(orientation: 'xy' | 'xz', size: number, divisions: number): Array<[Vec3, Vec3]> {
  const lines: Array<[Vec3, Vec3]> = [];
  const step = (size * 2) / divisions;
  for (let i = 0; i <= divisions; i++) {
    const v = -size + i * step;
    if (orientation === 'xy') {
      lines.push([{ x: -size, y: v, z: 0 }, { x: size, y: v, z: 0 }]);
      lines.push([{ x: v, y: -size, z: 0 }, { x: v, y: size, z: 0 }]);
    } else {
      lines.push([{ x: -size, y: 0, z: v }, { x: size, y: 0, z: v }]);
      lines.push([{ x: v, y: 0, z: -size }, { x: v, y: 0, z: size }]);
    }
  }
  return lines;
}

const GRID_PLANES = [buildGridPlane('xy', 1.05, 4), buildGridPlane('xz', 1.05, 4)];

interface StateConfig {
  color: [number, number, number];
  rotSpeed: number;
  pulse: number;
  radiusScale: number;
}

const STATE_CONFIG: Record<OrbState, StateConfig> = {
  idle: { color: [90, 170, 230], rotSpeed: 0.07, pulse: 0.02, radiusScale: 0.86 },
  listening: { color: [90, 200, 255], rotSpeed: 0.12, pulse: 0.06, radiusScale: 1.0 },
  thinking: { color: [170, 130, 255], rotSpeed: 0.4, pulse: 0.035, radiusScale: 0.95 },
  speaking: { color: [120, 255, 210], rotSpeed: 0.18, pulse: 0.14, radiusScale: 1.04 },
};

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}
function lerpConfig(a: StateConfig, b: StateConfig, t: number): StateConfig {
  return {
    color: [lerp(a.color[0], b.color[0], t), lerp(a.color[1], b.color[1], t), lerp(a.color[2], b.color[2], t)],
    rotSpeed: lerp(a.rotSpeed, b.rotSpeed, t),
    pulse: lerp(a.pulse, b.pulse, t),
    radiusScale: lerp(a.radiusScale, b.radiusScale, t),
  };
}

interface Projected {
  px: number;
  py: number;
  z: number;
  perspective: number;
}

function project(p: Vec3, cosA: number, sinA: number, tiltCos: number, tiltSin: number, r: number, cx: number, cy: number): Projected {
  const x1 = p.x * cosA - p.z * sinA;
  const z1 = p.x * sinA + p.z * cosA;
  const y = p.y * tiltCos - z1 * tiltSin;
  const z = p.y * tiltSin + z1 * tiltCos;
  const perspective = 420 / (420 - z * r);
  return { px: cx + x1 * r * perspective, py: cy + y * r * perspective, z, perspective };
}

/**
 * "Evolving neural BIM core" -- a rotating geodesic wireframe (structural
 * nodes + blueprint-line edges) with a secondary layer of fading neural
 * connections and travelling data-pulses along the edges. Deliberately NOT
 * a smooth particle globe. No live data by default; `state` reflects the
 * voice agent's real idle/listening/thinking/speaking state when embedded
 * in its pywebview window (see hooks/usePywebviewBridge.ts).
 */
export function OrbVisual({ size = 320, state = 'idle' }: OrbVisualProps) {
  const length = typeof size === 'number' ? `${size}px` : size;
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;

    let W = 0;
    let H = 0;
    let CX = 0;
    let CY = 0;
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      W = canvas.width = Math.max(1, Math.round(rect.width * dpr));
      H = canvas.height = Math.max(1, Math.round(rect.height * dpr));
      CX = W / 2;
      CY = H / 2;
    };
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);
    resize();

    let targetTiltX = 0;
    let tiltX = 0;
    const onMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      targetTiltX = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
    };
    window.addEventListener('mousemove', onMouseMove);

    let currentState = stateRef.current;
    let transitionT = 1;
    let prevConfig = STATE_CONFIG[currentState];
    let t = 0;
    let raf = 0;

    const animate = () => {
      raf = requestAnimationFrame(animate);
      if (canvas.getBoundingClientRect().width === 0) return; // hidden -- skip the work

      if (stateRef.current !== currentState) {
        prevConfig = lerpConfig(prevConfig, STATE_CONFIG[currentState], 1);
        currentState = stateRef.current;
        transitionT = 0;
      }
      t += 0.016;
      transitionT = Math.min(1, transitionT + 0.03);
      const cfg = lerpConfig(prevConfig, STATE_CONFIG[currentState], transitionT);
      tiltX = lerp(tiltX, targetTiltX, 0.04);

      // Crisp redraw each frame -- a blueprint reads as engineered/precise,
      // not a hazy trailing nebula.
      ctx.globalCompositeOperation = 'source-over';
      ctx.fillStyle = '#050a12';
      ctx.fillRect(0, 0, W, H);

      const angle = t * cfg.rotSpeed;
      const cosA = Math.cos(angle);
      const sinA = Math.sin(angle);
      const tiltCos = Math.cos(tiltX * 0.22);
      const tiltSin = Math.sin(tiltX * 0.22);
      const pulseAmt = 1 + Math.sin(t * 3.4) * cfg.pulse;
      const baseRadius = Math.min(W, H) * 0.44;
      const r = baseRadius * cfg.radiusScale * pulseAmt;
      const [cr, cg, cb] = cfg.color;

      // Soft ambient glow behind everything -- atmosphere without reading as a starfield.
      ctx.globalCompositeOperation = 'lighter';
      const haloGrad = ctx.createRadialGradient(CX, CY, 0, CX, CY, r * 1.15);
      haloGrad.addColorStop(0, `rgba(${cr}, ${cg}, ${cb}, 0.1)`);
      haloGrad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = haloGrad;
      ctx.beginPath();
      ctx.arc(CX, CY, r * 1.15, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalCompositeOperation = 'source-over';

      // Architectural reference grids -- rotate with the core, very faint.
      for (const plane of GRID_PLANES) {
        ctx.strokeStyle = `rgba(${cr}, ${cg}, ${cb}, 0.1)`;
        ctx.lineWidth = 1;
        for (const [p1, p2] of plane) {
          const a = project(p1, cosA, sinA, tiltCos, tiltSin, r, CX, CY);
          const b = project(p2, cosA, sinA, tiltCos, tiltSin, r, CX, CY);
          ctx.beginPath();
          ctx.moveTo(a.px, a.py);
          ctx.lineTo(b.px, b.py);
          ctx.stroke();
        }
      }

      const projectedVertices = CORE_VERTICES.map((v) => project(v, cosA, sinA, tiltCos, tiltSin, r, CX, CY));

      // Structural wireframe edges -- the rigid "blueprint" skeleton.
      for (const [a, b] of CORE_EDGES) {
        const pa = projectedVertices[a];
        const pb = projectedVertices[b];
        const depth = ((pa.z + pb.z) / 2 + 1) / 2;
        ctx.strokeStyle = `rgba(${cr}, ${cg}, ${cb}, ${0.14 + depth * 0.3})`;
        ctx.lineWidth = 0.6 + depth * 0.5;
        ctx.beginPath();
        ctx.moveTo(pa.px, pa.py);
        ctx.lineTo(pb.px, pb.py);
        ctx.stroke();
      }

      // Neural links -- evolving connections between non-adjacent nodes, fading in/out.
      for (const link of NEURAL_LINKS) {
        const alpha = 0.15 + 0.35 * Math.max(0, Math.sin(t * link.speed + link.phase));
        if (alpha < 0.05) continue;
        const pa = projectedVertices[link.a];
        const pb = projectedVertices[link.b];
        ctx.strokeStyle = `rgba(${Math.min(255, cr + 40)}, ${Math.min(255, cg + 40)}, 255, ${alpha})`;
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.moveTo(pa.px, pa.py);
        ctx.lineTo(pb.px, pb.py);
        ctx.stroke();
      }

      // Travelling data pulses along a subset of structural edges.
      ctx.globalCompositeOperation = 'lighter';
      for (const { edge, phase, speed } of PULSE_EDGES) {
        const pa = projectedVertices[edge[0]];
        const pb = projectedVertices[edge[1]];
        const progress = (t * speed + phase) % 1;
        const px = lerp(pa.px, pb.px, progress);
        const py = lerp(pa.py, pb.py, progress);
        ctx.beginPath();
        ctx.arc(px, py, 2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${Math.min(255, cr + 60)}, ${Math.min(255, cg + 60)}, 255, 0.85)`;
        ctx.fill();
      }
      ctx.globalCompositeOperation = 'source-over';

      // Structural nodes -- vertices, hub nodes (original icosahedron corners) drawn bigger/brighter.
      projectedVertices.forEach((p, i) => {
        const depth = (p.z + 1) / 2;
        const isHub = i < HUB_VERTEX_COUNT;
        const nodeSize = (isHub ? 2.6 : 1.4) * p.perspective * (0.55 + depth * 0.6);
        const alpha = 0.35 + depth * 0.55;
        ctx.beginPath();
        ctx.arc(p.px, p.py, Math.max(0.6, nodeSize), 0, Math.PI * 2);
        ctx.fillStyle = isHub
          ? `rgba(${Math.min(255, cr + 50)}, ${Math.min(255, cg + 50)}, 255, ${alpha})`
          : `rgba(${cr}, ${cg}, ${cb}, ${alpha})`;
        ctx.fill();
      });

      // Central hub glow -- the core "feels alive" even when idle.
      ctx.globalCompositeOperation = 'lighter';
      const coreGrad = ctx.createRadialGradient(CX, CY, 0, CX, CY, r * 0.22);
      coreGrad.addColorStop(0, 'rgba(255, 255, 255, 0.5)');
      coreGrad.addColorStop(0.5, `rgba(${cr}, ${cg}, ${cb}, 0.3)`);
      coreGrad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = coreGrad;
      ctx.beginPath();
      ctx.arc(CX, CY, r * 0.22, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalCompositeOperation = 'source-over';
    };
    raf = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(raf);
      resizeObserver.disconnect();
      window.removeEventListener('mousemove', onMouseMove);
    };
  }, []);

  return (
    <Box position="relative" w={length} h={length} borderRadius="full" overflow="hidden" aria-hidden="true">
      <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
    </Box>
  );
}
