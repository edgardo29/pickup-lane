import { Route, Routes } from 'react-router-dom'
import {
  CheckEmailPage,
  CreateAccountPage,
  FinishProfilePage,
  ForgotPasswordPage,
  SignInPage,
} from './pages/AuthPages.jsx'
import BrowseGamesPage from './pages/BrowseGamesPage.jsx'
import CreateGamePage from './pages/CreateGamePage.jsx'
import GameDetailsPage from './pages/GameDetailsPage.jsx'
import LandingPage from './pages/LandingPage.jsx'
import MyGamesPage from './pages/MyGamesPage.jsx'
import { EditProfilePage, ProfilePage, SettingsPage } from './pages/ProfilePages.jsx'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/sign-in" element={<SignInPage />} />
      <Route path="/create-account" element={<CreateAccountPage />} />
      <Route path="/finish-profile" element={<FinishProfilePage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/check-email" element={<CheckEmailPage />} />
      <Route path="/games" element={<BrowseGamesPage />} />
      <Route path="/games/:gameId" element={<GameDetailsPage />} />
      <Route path="/games/:gameId/edit" element={<CreateGamePage />} />
      <Route path="/my-games" element={<MyGamesPage />} />
      <Route path="/create-game" element={<CreateGamePage />} />
      <Route path="/profile" element={<ProfilePage />} />
      <Route path="/profile/edit" element={<EditProfilePage />} />
      <Route path="/settings" element={<SettingsPage />} />
    </Routes>
  )
}

export default App
