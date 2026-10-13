import { useState } from 'react';
import { Link, NavLink, Outlet } from 'react-router-dom';
import { useFieldMode } from '../theme/useFieldMode';
import { useAuth } from '../auth/useAuth';
import Starfield from './Starfield';
import AuthDialog from './AuthDialog';

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex-1 rounded-lg px-2 py-2 text-center font-display text-[13px] font-medium transition-colors sm:flex-none sm:px-3.5 sm:text-sm ${
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
  const { configured, user, loading, signOut } = useAuth();
  const [authOpen, setAuthOpen] = useState(false);

  return (
    <div className="nebula-bg relative min-h-svh">
      <div className="fixed inset-0 -z-10">
        <Starfield density={0.7} />
      </div>

      <header className="sticky top-0 z-20 border-b border-space-600/50 bg-space-950/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-2 gap-y-2 px-3 py-2.5 sm:flex-nowrap sm:gap-3 sm:px-6 sm:py-3">
          <Link to="/" className="flex min-w-0 items-center gap-2" aria-label="Stellinerary home">
            <span aria-hidden="true" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent/15 text-lg text-accent">
              ✦
            </span>
            <span className="hidden font-display text-base font-bold tracking-wide text-starlight min-[400px]:inline sm:text-lg">
              Stellinerary
            </span>
          </Link>
          <nav className="order-3 flex w-full items-center gap-0.5 sm:order-none sm:w-auto sm:gap-1" aria-label="Primary">
            <NavItem to="/" label="Mission" />
            <NavItem to="/plan" label="Plan" />
            <NavItem to="/trips" label="My trips" />
          </nav>
          <div className="flex shrink-0 items-center gap-1.5">
            {configured &&
              (loading ? null : user ? (
                <button
                  type="button"
                  onClick={() => void signOut()}
                  title={user.email ?? 'Signed in'}
                  className="max-w-28 truncate rounded-lg border border-space-600 px-2.5 py-1.5 font-display text-xs font-semibold text-stardim transition-colors hover:border-accent/50 hover:text-accent sm:max-w-40"
                >
                  {user.email ?? 'Account'} · out
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setAuthOpen(true)}
                  className="rounded-lg border border-accent/50 px-2.5 py-1.5 font-display text-xs font-semibold text-accent transition-colors hover:bg-accent/10"
                >
                  Sign in
                </button>
              ))}
            <button
              type="button"
              onClick={toggleFieldMode}
              aria-pressed={fieldMode}
              aria-label={fieldMode ? 'Leave red field mode' : 'Enter red field mode for use at the site'}
              title={fieldMode ? 'Leave red field mode' : 'Enter red field mode for use at the site'}
              className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 font-display text-xs font-semibold transition-colors sm:px-3 ${
                fieldMode
                  ? 'border-accent bg-accent/20 text-accent'
                  : 'border-space-600 text-stardim hover:border-accent/50 hover:text-accent'
              }`}
            >
              <span aria-hidden="true">{fieldMode ? '●' : '○'}</span>
              <span className="hidden sm:inline">{fieldMode ? 'Field mode on' : 'Field mode'}</span>
            </button>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto w-full max-w-6xl px-4 pb-20 sm:px-6">
        <Outlet />
      </main>

      <AuthDialog key={String(authOpen)} open={authOpen} onClose={() => setAuthOpen(false)} />

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
