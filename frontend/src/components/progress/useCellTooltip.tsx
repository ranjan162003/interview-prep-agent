import { useCallback, useRef, useState, type FocusEvent, type PointerEvent, type ReactNode } from "react";

interface TooltipState {
  lines: ReactNode[];
  x: number;
  y: number;
}

/**
 * One shared hover/focus tooltip for a grid of chart cells. Cells get `cellProps(lines)`;
 * the container renders `tooltip` and needs `position: relative` (via `containerRef`).
 */
export function useCellTooltip() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<TooltipState | null>(null);

  const showFor = useCallback((target: Element, lines: ReactNode[]) => {
    const container = containerRef.current;
    if (!container) return;
    const box = container.getBoundingClientRect();
    const cell = target.getBoundingClientRect();
    setState({ lines, x: cell.left - box.left + cell.width / 2, y: cell.top - box.top });
  }, []);

  const hide = useCallback(() => setState(null), []);

  const cellProps = (lines: ReactNode[]) => ({
    tabIndex: 0,
    onPointerEnter: (event: PointerEvent<HTMLElement>) => showFor(event.currentTarget, lines),
    onFocus: (event: FocusEvent<HTMLElement>) => showFor(event.currentTarget, lines),
    onPointerLeave: hide,
    onBlur: hide,
  });

  const tooltip = state ? (
    <div className="chart-tooltip" style={{ left: state.x, top: state.y }} role="tooltip">
      {state.lines.map((line, i) => (
        <div key={i} className={i === 0 ? "chart-tooltip__title" : undefined}>
          {line}
        </div>
      ))}
    </div>
  ) : null;

  return { containerRef, cellProps, tooltip };
}
