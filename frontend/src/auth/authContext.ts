import { createContext } from 'react';
import type { Session, User } from '@supabase/supabase-js';

export interface AuthValue {
  configured: boolean;
  session: Session | null;
  user: User | null;
  loading: boolean;
  signInWithGoogle: () => Promise<void>;
  signUpWithEmail: (email: string, password: string) => Promise<{ needsConfirmation: boolean }>;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthValue>({
  configured: false,
  session: null,
  user: null,
  loading: false,
  signInWithGoogle: async () => {},
  signUpWithEmail: async () => ({ needsConfirmation: false }),
  signInWithEmail: async () => {},
  signOut: async () => {},
});
