import { BarChart3, CalendarCheck, Dumbbell, Menu, Mic, type LucideIcon } from "lucide-react";
import { NavLink } from "react-router-dom";

const TABS: { to: string; label: string; icon: LucideIcon; end?: boolean }[] = [
  { to: "/", label: "Today", icon: CalendarCheck, end: true },
  { to: "/practice", label: "Practice", icon: Dumbbell },
  { to: "/mock-interview", label: "Mock", icon: Mic },
  { to: "/progress", label: "Progress", icon: BarChart3 },
];

/** Phone-only bottom navigation; "More" opens the full sidebar (coach, connectors, settings, theme). */
export function MobileTabBar({ onOpenMore }: { onOpenMore: () => void }) {
  return (
    <nav className="mobile-tabbar" aria-label="Quick navigation">
      {TABS.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) => `mobile-tabbar__tab${isActive ? " mobile-tabbar__tab--active" : ""}`}
        >
          <Icon size={20} aria-hidden="true" />
          <span>{label}</span>
        </NavLink>
      ))}
      <button type="button" className="mobile-tabbar__tab" onClick={onOpenMore}>
        <Menu size={20} aria-hidden="true" />
        <span>More</span>
      </button>
    </nav>
  );
}
