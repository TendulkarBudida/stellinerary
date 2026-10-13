import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { Session } from '@supabase/supabase-js';
import { isSupabaseConfigured, supabase } from './supabase';
import { AuthContext } from './authContext';
import type { AuthValue } from './authContext';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(isSupabaseConfigured);

  useEffect(() => {
    if (!supabase) return;
    let alive = true;
    (async () => {
      const { data } = await supabase.auth.getSession();
      if (alive) {
        setSession(data.session);
        setLoading(false);
      }
    })();
    const { data: listener } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      setLoading(false);
    });
    return () => {
      alive = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  const signInWithGoogle = useCallback(async () => {
    if (!supabase) throw new Error('Sign-in is not configured yet.');
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    });
    if (error) throw error;
  }, []);

  const signUpWithEmail = useCallback(async (email: string, password: string) => {
    if (!supabase) throw new Error('Sign-in is not configured yet.');
    const { data, error } = await supabase.auth.signUp({ email, password });
    if (error) throw error;
    return { needsConfirmation: !data.session };
  }, []);

  const signInWithEmail = useCallback(async (email: string, password: string) => {
    if (!supabase) throw new Error('Sign-in is not configured yet.');
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
  }, []);

  const signOut = useCallback(async () => {
    if (!supabase) return;
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
  }, []);

  const value = useMemo<AuthValue>(
    () => ({
      configured: isSupabaseConfigured,
      session,
      user: session?.user ?? null,
      loading,
      signInWithGoogle,
      signUpWithEmail,
      signInWithEmail,
      signOut,
    }),
    [session, loading, signInWithGoogle, signUpWithEmail, signInWithEmail, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
