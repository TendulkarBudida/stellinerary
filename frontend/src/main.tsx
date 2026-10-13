import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { FieldModeProvider } from './theme/FieldMode.tsx'
import { AuthProvider } from './auth/AuthContext.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <FieldModeProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </FieldModeProvider>
    </BrowserRouter>
  </StrictMode>,
)
