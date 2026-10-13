import { createContext } from 'react';

export interface FieldModeValue {
  fieldMode: boolean;
  toggleFieldMode: () => void;
}

export const FieldModeContext = createContext<FieldModeValue>({
  fieldMode: false,
  toggleFieldMode: () => {},
});
