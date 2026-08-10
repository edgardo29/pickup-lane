import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './context/AuthProvider.jsx'
import { StepUpProvider } from './context/StepUpProvider.jsx'
import './styles/base.css'
import './styles/app-shell.css'
import './styles/game-card.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <StepUpProvider>
          <App />
        </StepUpProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
