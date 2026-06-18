import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AppPageHeader } from '../../components/app/index.js'
import { ProfileEditModal } from './ProfileEditModal.jsx'
import { ProfileHero } from './ProfileHero.jsx'
import { ProfileShell } from './ProfileShell.jsx'
import { ProfileSkeleton } from './ProfileSkeleton.jsx'
import { ProfileState } from './ProfileState.jsx'
import { ProfileStats } from './ProfileStats.jsx'
import SettingsContent from './SettingsContent.jsx'
import { useSettingsPageModel } from './useSettingsPageModel.jsx'

export function ProfilePage({ isEditProfileOpen = false }) {
  const navigate = useNavigate()
  const [isLocalEditOpen, setIsLocalEditOpen] = useState(false)
  const profilePage = useSettingsPageModel()
  const isEditOpen = isEditProfileOpen || isLocalEditOpen
  const openEditProfile = useCallback(() => {
    setIsLocalEditOpen(true)
  }, [])
  const closeEditProfile = useCallback(() => {
    if (isEditProfileOpen) {
      navigate('/profile', { replace: true })
      return
    }

    setIsLocalEditOpen(false)
  }, [isEditProfileOpen, navigate])
  const handleEditProfileSaved = useCallback((savedProfile) => {
    profilePage.handleProfileSaved(savedProfile)
    closeEditProfile()
  }, [closeEditProfile, profilePage])

  if (profilePage.status === 'loading') {
    return (
      <ProfileShell>
        <ProfileSkeleton />
      </ProfileShell>
    )
  }

  if (profilePage.status !== 'success') {
    return <ProfileShell state={<ProfileState title="Could not load profile" message={profilePage.error} />} />
  }

  return (
    <ProfileShell>
      <AppPageHeader title="Profile" subtitle="Manage your profile, preferences, and account." />
      <div className="profile-hub">
        <section className="profile-overview-card">
          <ProfileHero
            currentUser={profilePage.currentUser}
            gameCreditBalance={profilePage.gameCreditBalance}
            onEditProfile={openEditProfile}
            settings={profilePage.settings}
          />
          <ProfileStats stats={profilePage.stats} />
        </section>
        <SettingsContent {...profilePage} />
      </div>
      {isEditOpen && (
        <ProfileEditModal
          currentUser={profilePage.currentUser}
          firebaseUser={profilePage.firebaseUser}
          onClose={closeEditProfile}
          onSaved={handleEditProfileSaved}
          settings={profilePage.settings}
        />
      )}
    </ProfileShell>
  )
}
