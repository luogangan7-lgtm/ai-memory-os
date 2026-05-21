// AI Memory OS brand mark.
//
// Three nested rings represent the L1/L2/L3 memory tiers; the offset solid
// node is the currently-active focal memory, with a slow pulse that doubles
// as a system-online indicator. Single-color via var(--v6-accent), so it
// flips correctly between the light and dark themes.

interface V6LogoProps {
  size?: number;
  breathing?: boolean;
  className?: string;
}

export function V6Logo({ size = 22, breathing = false, className }: V6LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      role="img"
      aria-label="AI Memory OS"
      className={className}
    >
      <circle cx="12" cy="12" r="9" stroke="var(--v6-accent)" strokeWidth="1" opacity="0.35" />
      <circle cx="12" cy="12" r="5.75" stroke="var(--v6-accent)" strokeWidth="1.25" opacity="0.7" />
      <circle
        cx="13.6"
        cy="10.4"
        r="2.4"
        fill="var(--v6-accent)"
        className={breathing ? "v6-logo__core" : undefined}
      />
    </svg>
  );
}
