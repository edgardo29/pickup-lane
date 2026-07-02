import { AppFooter } from './components/app/index.js'
import { AppRoutes } from './routes/AppRoutes.jsx'
import { ScrollToTop } from './routes/ScrollToTop.jsx'

function App() {
  return (
    <div className="app-root">
      <ScrollToTop />
      <AppRoutes />
      <AppFooter />
    </div>
  )
}

export default App
