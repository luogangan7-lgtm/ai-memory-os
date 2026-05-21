// Cortex brand mark.
//
// Geometric C with an off-axis firing node. The C reads as both the letter
// (wordmark anchor) and as a half-open ring (cortex / containment). The solid
// dot at the C's opening is the "firing neuron" — the breathing pulse signals
// the system is alive and doubles as the lone touch of motion in an otherwise
// stationary monochrome composition.

interface CortexMarkProps {
  size?: number;
  breathing?: boolean;
  className?: string;
}

export function CortexMark({ size = 22, breathing = false, className }: CortexMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      role="img"
      aria-label="Cortex"
      className={className}
    >
      {/* C arc — open on the right, stroked thick for a confident letterform */}
      <path
        d="M 17.5 6.4 A 7.6 7.6 0 1 0 17.5 17.6"
        stroke="currentColor"
        strokeWidth="2.1"
        strokeLinecap="round"
        fill="none"
      />
      {/* Firing node, sitting where the C "would close" */}
      <circle
        cx="18.2"
        cy="12"
        r="1.85"
        fill="currentColor"
        className={breathing ? "v6-logo__core" : undefined}
      />
    </svg>
  );
}
