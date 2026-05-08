import { Navigate, Route, Routes } from 'react-router-dom'
import {
  CheckEmailPage,
  CreateAccountPage,
  FinishProfilePage,
  ForgotPasswordPage,
  ResetPasswordPage,
  SignInPage,
} from './pages/AuthPages.jsx'
import BrowseGamesPage from './pages/BrowseGamesPage.jsx'
import CreateGamePage from './pages/CreateGamePage.jsx'
import GameDetailsPage from './pages/GameDetailsPage.jsx'
import InboxPage from './pages/InboxPage.jsx'
import LandingPage from './pages/LandingPage.jsx'
import { PrivacyPage, TermsPage } from './pages/LegalPages.jsx'
import MyGamesPage from './pages/MyGamesPage.jsx'
import PlayerHubPage from './pages/PlayerHubPage.jsx'
import { EditProfilePage, ProfilePage, SettingsPage } from './pages/ProfilePages.jsx'
import { useAuth } from './hooks/useAuth.js'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/sign-in" element={<SignInPage />} />
      <Route path="/create-account" element={<CreateAccountPage />} />
      <Route path="/finish-profile" element={<FinishProfilePage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/check-email" element={<CheckEmailPage />} />
      <Route path="/terms" element={<TermsPage />} />
      <Route path="/privacy" element={<PrivacyPage />} />
      <Route path="/games" element={<BrowseGamesPage />} />
      <Route path="/games/:gameId" element={<GameDetailsPage />} />
      <Route
        path="/games/:gameId/edit"
        element={
          <RequireAppUser>
            <CreateGamePage />
          </RequireAppUser>
        }
      />
      <Route
        path="/my-games"
        element={
          <RequireAppUser>
            <MyGamesPage />
          </RequireAppUser>
        }
      />
      <Route
        path="/inbox"
        element={
          <RequireAppUser>
            <InboxPage />
          </RequireAppUser>
        }
      />
      <Route
        path="/player-hub"
        element={
          <RequireAppUser>
            <PlayerHubPage />
          </RequireAppUser>
        }
      />
      <Route
        path="/create-game"
        element={
          <RequireAppUser>
            <CreateGamePage />
          </RequireAppUser>
        }
      />
      <Route
        path="/profile"
        element={
          <RequireAppUser>
            <ProfilePage />
          </RequireAppUser>
        }
      />
      <Route
        path="/profile/edit"
        element={
          <RequireAppUser>
            <EditProfilePage />
          </RequireAppUser>
        }
      />
      <Route
        path="/settings"
        element={
          <RequireAppUser>
            <SettingsPage />
          </RequireAppUser>
        }
      />
    </Routes>
  )
}

function RequireAppUser({ children }) {
  const { appUser, isLoading } = useAuth()

  if (isLoading) {
    return null
  }

  if (!appUser) {
    return <Navigate to="/" replace />
  }

  return children
}

export default App
