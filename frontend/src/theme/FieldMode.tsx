import { useCallback, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { FieldModeContext } from './fieldModeContext';

const STORAGE_KEY = 'stellinerary-field-mode';

export function FieldModeProvider({ children }: { children: ReactNode }) {
  const [fieldMode, setFieldMode] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === '1';
    } catch {
      return false;
    }
  });

  useEffect(() => {
    document.documentElement.classList.toggle('field-mode', fieldMode);
    try {
      localStorage.setItem(STORAGE_KEY, fieldMode ? '1' : '0');
    } catch {
      /* storage unavailable — mode still applies for this session */
    }
  }, [fieldMode]);

  const toggleFieldMode = useCallback(() => setFieldMode((v) => !v), []);

  return (
    <FieldModeContext.Provider value={{ fieldMode, toggleFieldMode }}>
      {children}
    </FieldModeContext.Provider>
  );
}
