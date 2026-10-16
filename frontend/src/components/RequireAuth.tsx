import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from '../auth/useAuth';
import AuthDialog from './AuthDialog';
import { Button, Card } from './ui';

/**
 * Gate for pages that require an account. The landing page stays public;
 * everything else redirects here into a sign-in prompt when logged out.
 * When auth is not configured (local dev without keys), pages stay open.
 */
export default function RequireAuth({ children }: { children: ReactNode }) {
  const { configured, user, loading } = useAuth();
  const [authOpen, setAuthOpen] = useState(false);

  if (!configured || user) {
    return <>{children}</>;
  }

  if (loading) {
    return <p className="pt-16 text-center text-sm text-stardim">Checking your session…</p>;
  }

  return (
    <div className="mx-auto max-w-lg pt-10 sm:pt-16">
      <Card className="relative overflow-hidden p-6 text-center sm:p-8">
        <p aria-hidden="true" className="text-3xl text-accent">✦</p>
        <h1 className="mt-3 font-display text-2xl font-bold text-starlight">Sign in to continue</h1>
        <p className="mx-auto mt-2 max-w-sm text-sm text-stardim">
          Expedition planning and saved trips need an account — your plans persist under it.
        </p>
        <div className="mt-6 flex flex-col justify-center gap-2.5 sm:flex-row">
          <Button onClick={() => setAuthOpen(true)}>Sign in / Sign up</Button>
          <Link to="/">
            <Button variant="ghost" className="w-full sm:w-auto">Back to mission</Button>
          </Link>
        </div>
      </Card>
      <AuthDialog key={String(authOpen)} open={authOpen} onClose={() => setAuthOpen(false)} />
    </div>
  );
}
