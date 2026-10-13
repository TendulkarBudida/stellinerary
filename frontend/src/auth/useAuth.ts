import { useContext } from 'react';
import { AuthContext } from './authContext';
import type { AuthValue } from './authContext';

export function useAuth(): AuthValue {
  return useContext(AuthContext);
}
