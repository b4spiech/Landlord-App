import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { ToastProvider } from './components/Toast.tsx'
import { isPublicSite } from './site.ts'

// Each site is its own lazily-loaded bundle, so public visitors don't
// download the landlord app.
// eslint-disable-next-line react-refresh/only-export-components -- entry file, never hot-reloaded as a module
const Root = isPublicSite()
  ? lazy(() => import('./public/PublicApp.tsx'))
  : lazy(() => import('./App.tsx'))

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ToastProvider>
      <Suspense fallback={null}>
        <Root />
      </Suspense>
    </ToastProvider>
  </StrictMode>,
)
