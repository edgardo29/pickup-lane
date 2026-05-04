import { Route, Routes } from 'react-router-dom'
import BrowseGamesPage from './pages/BrowseGamesPage.jsx'
import LandingPage from './pages/LandingPage.jsx'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/games" element={<BrowseGamesPage />} />
    </Routes>
  )
}

export default App
