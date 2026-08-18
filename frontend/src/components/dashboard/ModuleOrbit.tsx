import type { ComponentType } from 'react';
import { Box, Text } from '@chakra-ui/react';
import { Link as RouterLink } from 'react-router-dom';
import { OrbVisual } from './OrbVisual';
import type { OrbState } from './OrbVisual';
import type { DashboardIconProps } from './icons';

export interface OrbitModule {
  key: string;
  label: string;
  description: string;
  to: string;
  Icon: ComponentType<DashboardIconProps>;
}

export interface ModuleOrbitProps {
  items: OrbitModule[];
  /** Live voice-agent state when embedded in its pywebview window (see usePywebviewBridge). Defaults to 'idle'. */
  orbState?: OrbState;
}

// Coordinate slots on a 720x340 design canvas -- converted to percentages
// below so the layout scales fluidly with the available height instead of
// forcing a fixed pixel size on its grid track.
const CANVAS_W = 720;
const CANVAS_H = 340;

const GLOBE_LEFT = 250;
const GLOBE_TOP = 60;
const GLOBE_SIZE = 220;
const GLOBE_CX = GLOBE_LEFT + GLOBE_SIZE / 2;
const GLOBE_CY = GLOBE_TOP + GLOBE_SIZE / 2;
const GLOBE_R = GLOBE_SIZE / 2;

// Sphere-side line endpoints computed to sit exactly on the globe's own
// circle (rather than hand-picked coordinates that drift out of alignment
// whenever the globe's size/position changes).
function spherePoint(angleDeg: number): [number, number] {
  const rad = (angleDeg * Math.PI) / 180;
  return [GLOBE_CX + GLOBE_R * Math.cos(rad), GLOBE_CY + GLOBE_R * Math.sin(rad)];
}

const SLOTS = [
  { side: 'left' as const, sphere: spherePoint(-145), dot: [156, 50] as [number, number] },
  { side: 'right' as const, sphere: spherePoint(-35), dot: [564, 50] as [number, number] },
  { side: 'left' as const, sphere: spherePoint(180), dot: [156, 170] as [number, number] },
  { side: 'right' as const, sphere: spherePoint(0), dot: [564, 170] as [number, number] },
  { side: 'left' as const, sphere: spherePoint(145), dot: [156, 290] as [number, number] },
  { side: 'right' as const, sphere: spherePoint(35), dot: [564, 290] as [number, number] },
];

const pctX = (v: number) => `${(v / CANVAS_W) * 100}%`;
const pctY = (v: number) => `${(v / CANVAS_H) * 100}%`;

/** Connector-line labels radiating from the globe, matching the reference HUD layout -- real REVVY modules only. */
export function ModuleOrbit({ items, orbState = 'idle' }: ModuleOrbitProps) {
  const slotted = items.slice(0, 6).map((item, i) => ({ item, slot: SLOTS[i] }));

  return (
    // w/h both "full" (not an aspectRatio derived from height alone) --
    // deriving width purely from height let this render wider than its
    // actual grid column at some window sizes, with the labels at both
    // edges then hard-clipped by the frame's overflow:hidden. Filling
    // exactly what the parent gives it guarantees every percentage-
    // positioned label inside stays within the real visible bounds.
    <Box position="relative" w="full" h="full" mx="auto" display={{ base: 'none', md: 'block' }}>
      <Box position="absolute" left={pctX(GLOBE_LEFT)} top={pctY(GLOBE_TOP)} w={pctX(GLOBE_SIZE)} aspectRatio={1}>
        <OrbVisual size="100%" state={orbState} />
      </Box>

      <svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
        preserveAspectRatio="none"
        style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
      >
        {slotted.map(({ item, slot }) => (
          <g key={item.key} stroke="#38e0ff" strokeOpacity="0.5" strokeWidth="1">
            <line x1={slot.sphere[0]} y1={slot.sphere[1]} x2={slot.dot[0]} y2={slot.dot[1]} />
            <circle cx={slot.sphere[0]} cy={slot.sphere[1]} r="2.5" fill="#38e0ff" stroke="none" />
            <circle cx={slot.dot[0]} cy={slot.dot[1]} r="2.5" fill="#38e0ff" stroke="none" />
          </g>
        ))}
      </svg>

      {slotted.map(({ item, slot }) => {
        // Capped by whichever is smaller: 160px, or however much room is
        // actually left to the container's edge on that side -- a fixed
        // 160px alone can still push past the edge on narrower windows
        // where the side panels eat into the center column more than the
        // 720-unit design canvas assumed (the fix to the container itself
        // stopped it overflowing the *frame*, but not this).
        const labelWidth =
          slot.side === 'left' ? `min(160px, ${pctX(slot.dot[0])})` : `min(160px, calc(100% - ${pctX(slot.dot[0])}))`;
        const left = slot.side === 'left' ? `calc(${pctX(slot.dot[0])} - ${labelWidth})` : pctX(slot.dot[0]);

        return (
          <Box
            key={item.key}
            asChild
            position="absolute"
            top={`calc(${pctY(slot.dot[1])} - 18px)`}
            left={left}
            w={labelWidth}
            textAlign="center"
            cursor="pointer"
            transition="all 0.15s ease"
            _hover={{ transform: `translateX(${slot.side === 'left' ? '-4px' : '4px'})` }}
          >
            <RouterLink to={item.to}>
            <Box display="flex" flexDirection="column" alignItems="center" gap={0.5}>
              <Box color="cyan.300">
                <item.Icon size={14} />
              </Box>
              <Text fontSize="11px" fontWeight="bold" letterSpacing="wide" color="whiteAlpha.900" lineClamp={1}>
                {item.label.toUpperCase()}
              </Text>
              <Text fontSize="10px" color="whiteAlpha.500" lineClamp={1}>
                {item.description}
              </Text>
            </Box>
          </RouterLink>
        </Box>
        );
      })}
    </Box>
  );
}
