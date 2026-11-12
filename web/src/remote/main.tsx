import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Remote from './Remote'
import './remote.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Remote />
  </StrictMode>,
)
