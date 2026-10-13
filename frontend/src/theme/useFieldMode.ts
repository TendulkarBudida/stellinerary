import { useContext } from 'react';
import { FieldModeContext } from './fieldModeContext';

export function useFieldMode() {
  return useContext(FieldModeContext);
}
