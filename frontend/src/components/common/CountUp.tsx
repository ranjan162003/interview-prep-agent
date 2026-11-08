import { useEffect, useRef, useState } from "react";

interface CountUpProps {
  value: number;
  format: (value: number) => string;
  durationMs?: number;
}

/** A number that counts up to its value when it first appears (or changes). Instant if the user prefers less motion. */
export function CountUp({ value, format, durationMs = 900 }: CountUpProps) {
  const [shown, setShown] = useState(value);
  const from = useRef(0);

  useEffect(() => {
    const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion || !Number.isFinite(value)) {
      setShown(value);
      return;
    }
    const start = performance.now();
    const startValue = from.current;
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      setShown(startValue + (value - startValue) * eased);
      if (t < 1) frame = requestAnimationFrame(tick);
      else from.current = value;
    };
    frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      from.current = value;
    };
  }, [value, durationMs]);

  // The accessible value is always the final one; only the visible digits animate.
  return (
    <>
      <span aria-hidden="true">{format(shown)}</span>
      <span className="visually-hidden">{format(value)}</span>
    </>
  );
}
