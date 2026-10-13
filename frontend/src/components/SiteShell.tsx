import { Link, NavLink, Outlet } from 'react-router-dom';
import { useFieldMode } from '../theme/useFieldMode';
import Starfield from './Starfield';

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `rounded-lg px-3.5 py-2 font-display text-sm font-medium transition-colors ${
          isActive ? 'bg-accent/15 text-accent' : 'text-stardim hover:text-starlight'
        }`
      }
    >
      {label}
    </NavLink>
  );
}

export default function SiteShell() {
  const { fieldMode, toggleFieldMode } = useFieldMode();

  return (
    <div className="nebula-bg relative min-h-svh">
      <div className="fixed inset-0 -z-10">
        <Starfield density={0.7} />
      </div>

      <header className="sticky top-0 z-20 border-b border-space-600/50 bg-space-950/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link to="/" className="flex items-center gap-2.5">
            <span aria-hidden="true" className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/15 text-lg text-accent">
              ✦
            </span>
            <span className="font-display text-lg font-bold tracking-wide text-starlight">
              Stellinerary
            </span>
          </Link>
          <nav className="flex items-center gap-1" aria-label="Primary">
            <NavItem to="/" label="Mission" />
            <NavItem to="/plan" label="Plan" />
            <NavItem to="/trips" label="My trips" />
          </nav>
          <button
            type="button"
            onClick={toggleFieldMode}
            aria-pressed={fieldMode}
            title={fieldMode ? 'Leave red field mode' : 'Enter red field mode for use at the site'}
            className={`rounded-lg border px-3 py-1.5 font-display text-xs font-semibold transition-colors ${
              fieldMode
                ? 'border-accent bg-accent/20 text-accent'
                : 'border-space-600 text-stardim hover:border-accent/50 hover:text-accent'
            }`}
          >
            {fieldMode ? '● Field mode on' : '○ Field mode'}
          </button>
        </div>
      </header>

      <main className="relative z-10 mx-auto w-full max-w-6xl px-4 pb-20 sm:px-6">
        <Outlet />
      </main>

      <footer className="relative z-10 border-t border-space-600/50 py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-2 px-4 text-center sm:px-6">
          <p className="font-display text-sm font-semibold text-stardim">Stellinerary</p>
          <p className="max-w-md text-xs text-starfaint">
            Deterministic expedition planning. Forecasts are only shown when they cover your night;
            stories are optional and never drive decisions.
          </p>
        </div>
      </footer>
    </div>
  );
}
