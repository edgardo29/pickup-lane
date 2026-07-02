import { useLocation } from 'react-router-dom'
import { AppFooter } from './components/app/index.js'
import { AppRoutes } from './routes/AppRoutes.jsx'
import { ScrollToTop } from './routes/ScrollToTop.jsx'

function App() {
  const location = useLocation()
  const hideFooter = isAuthRoute(location.pathname)

  return (
    <div className="app-root">
      <ScrollToTop />
      <AppRoutes />
      {!hideFooter && <AppFooter />}
    </div>
  )
}

function isAuthRoute(pathname) {
  return [
    '/admin/sign-in',
    '/check-email',
    '/create-account',
    '/finish-profile',
    '/forgot-password',
    '/reset-password',
    '/sign-in',
  ].includes(pathname)
}

export default App
