// Minimal hand-rolled line icons for the dashboard (no icon library
// dependency). Each renders `currentColor` so callers set color via the
// Chakra `color` prop on a wrapping element.
export interface DashboardIconProps {
  size?: number;
}

const base = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.6,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
};

export function ChatIcon({ size = 20 }: DashboardIconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M4 5h16v11H8l-4 4V5Z" />
    </svg>
  );
}

export function ShieldCheckIcon({ size = 20 }: DashboardIconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3Z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

export function CubeIcon({ size = 20 }: DashboardIconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3Z" />
      <path d="M4.5 7.5L12 12l7.5-4.5" />
      <path d="M12 12v9" />
    </svg>
  );
}

export function ChartIcon({ size = 20 }: DashboardIconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M4 20V10M12 20V4M20 20v-7" />
      <path d="M4 20h16" />
    </svg>
  );
}

export function BookIcon({ size = 20 }: DashboardIconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M5 4h9a3 3 0 0 1 3 3v13H8a3 3 0 0 0-3 3V4Z" />
      <path d="M17 20H8" />
    </svg>
  );
}

export function UsersIcon({ size = 20 }: DashboardIconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <circle cx="9" cy="8" r="3" />
      <path d="M3 20c0-3.3 2.7-5 6-5s6 1.7 6 5" />
      <circle cx="17" cy="9" r="2.4" />
      <path d="M15.5 20c.2-2.6 1.8-4 3.5-4.4" />
    </svg>
  );
}

export function MicIcon({ size = 20 }: DashboardIconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0" />
      <path d="M12 18v3M9 21h6" />
    </svg>
  );
}

export function SendIcon({ size = 20 }: DashboardIconProps) {
  // A simple arrow rather than a paper-plane silhouette -- the plane shape's
  // bounding box was mathematically centered but its visual weight (wide
  // base, thin tip) still read as off-center inside a circular button. This
  // is symmetric on both axes.
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M5 12h13M13 6l6 6-6 6" />
    </svg>
  );
}

export function PlusIcon({ size = 20 }: DashboardIconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function ChevronRightIcon({ size = 20 }: DashboardIconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M9 5l7 7-7 7" />
    </svg>
  );
}

export function MenuIcon({ size = 20 }: DashboardIconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  );
}

export function ClockIcon({ size = 20 }: DashboardIconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </svg>
  );
}

export function CheckCircleIcon({ size = 20 }: DashboardIconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M8.5 12.3l2.3 2.3 4.7-5" />
    </svg>
  );
}
