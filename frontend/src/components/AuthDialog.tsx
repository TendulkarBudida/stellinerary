import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../auth/useAuth';
import { isValidCredentials } from '../auth/validation';
import { Button } from './ui';

const inputCls =
  'w-full rounded-lg border border-space-600 bg-space-950 px-3.5 py-2.5 text-base text-starlight placeholder:text-starfaint focus:border-accent focus:outline-none sm:text-sm';
const labelCls = 'mb-1.5 block font-display text-xs font-semibold uppercase tracking-wider text-stardim';

function friendlyError(err: unknown): string {
  const message = err instanceof Error ? err.message : 'Something went wrong.';
  if (/provider.*not.*enabled|unsupported provider/i.test(message)) {
    return 'Google sign-in is not switched on yet. Use email for now — Google lands as the final auth step.';
  }
  if (/invalid login credentials/i.test(message)) {
    return 'Email or password is incorrect. New here? Switch to the Sign up tab.';
  }
  if (/email not confirmed/i.test(message)) {
    return 'Please confirm your email first — check your inbox for the confirmation link.';
  }
  if (/password.*short|password.*6/i.test(message)) {
    return 'Password must be at least 6 characters.';
  }
  return message;
}

export default function AuthDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { signInWithGoogle, signUpWithEmail, signInWithEmail } = useAuth();
  const [tab, setTab] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const emailRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    const id = window.setTimeout(() => emailRef.current?.focus(), 60);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.clearTimeout(id);
      window.removeEventListener('keydown', onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  const valid = isValidCredentials(email, password);

  const handleGoogle = async () => {
    setBusy(true);
    setError(null);
    try {
      await signInWithGoogle();
    } catch (err: unknown) {
      setError(friendlyError(err));
      setBusy(false);
    }
  };

  const handleEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!valid || busy) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (tab === 'signup') {
        const { needsConfirmation } = await signUpWithEmail(email.trim(), password);
        if (needsConfirmation) {
          setNotice('Account created — check your inbox for the confirmation link, then sign in.');
        } else {
          onClose();
        }
      } else {
        await signInWithEmail(email.trim(), password);
        onClose();
      }
    } catch (err: unknown) {
      setError(friendlyError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-4 backdrop-blur-sm sm:items-center"
      onClick={onClose}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={tab === 'signin' ? 'Sign in' : 'Create account'}
        className="w-full max-w-md rounded-2xl border border-space-600/60 bg-space-900 p-5 shadow-[0_8px_60px_rgba(0,0,0,0.6)] sm:p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-xl font-bold text-starlight">
              {tab === 'signin' ? 'Welcome back' : 'Join the expedition'}
            </h2>
            <p className="mt-0.5 text-sm text-stardim">Signed-in trips persist under your account.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close sign-in dialog"
            className="rounded-lg px-2 py-1 text-xl leading-none text-starfaint hover:text-starlight"
          >
            ×
          </button>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-1 rounded-lg bg-space-950 p-1" role="tablist" aria-label="Sign in or sign up">
          {(['signin', 'signup'] as const).map((t) => (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={tab === t}
              onClick={() => { setTab(t); setError(null); setNotice(null); }}
              className={`rounded-md px-3 py-2 font-display text-sm font-semibold transition-colors ${
                tab === t ? 'bg-accent/15 text-accent' : 'text-stardim hover:text-starlight'
              }`}
            >
              {t === 'signin' ? 'Sign in' : 'Sign up'}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={() => void handleGoogle()}
          disabled={busy}
          className="mt-4 flex w-full items-center justify-center gap-2.5 rounded-lg border border-space-600 bg-space-950 px-4 py-2.5 font-display text-sm font-semibold text-starlight transition-colors hover:border-accent/50 disabled:opacity-50"
        >
          <span aria-hidden="true" className="font-bold">
            <span className="text-[#4285F4]">G</span>
          </span>
          Continue with Google
        </button>

        <div className="my-4 flex items-center gap-3" aria-hidden="true">
          <hr className="rule-glow flex-1" />
          <span className="text-xs text-starfaint">or with email</span>
          <hr className="rule-glow flex-1" />
        </div>

        <form onSubmit={(e) => void handleEmail(e)}>
          <div>
            <label className={labelCls} htmlFor="auth-email">Email</label>
            <input
              id="auth-email"
              ref={emailRef}
              className={inputCls}
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@nightsky.in"
              required
            />
          </div>
          <div className="mt-3">
            <label className={labelCls} htmlFor="auth-password">Password</label>
            <input
              id="auth-password"
              className={inputCls}
              type="password"
              autoComplete={tab === 'signin' ? 'current-password' : 'new-password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 6 characters"
              required
            />
          </div>

          {error && (
            <p className="mt-3 rounded-lg border border-danger/40 bg-danger/10 p-3 text-[13px] text-danger" role="alert">
              {error}
            </p>
          )}
          {notice && (
            <p className="mt-3 rounded-lg border border-success/40 bg-success/10 p-3 text-[13px] text-success" role="status">
              {notice}
            </p>
          )}

          <Button type="submit" disabled={busy || !valid} className="mt-4 w-full">
            {busy ? 'Please wait…' : tab === 'signin' ? 'Sign in' : 'Create account'}
          </Button>
        </form>
      </div>
    </div>
  );
}
