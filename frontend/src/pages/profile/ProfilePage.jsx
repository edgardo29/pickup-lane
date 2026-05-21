import { AppPageHeader } from '../../components/app/index.js'
import { ProfileHero } from './ProfileHero.jsx'
import { ProfileShell } from './ProfileShell.jsx'
import { ProfileState } from './ProfileState.jsx'
import { ProfileStats } from './ProfileStats.jsx'
import { useProfileContext } from './useProfileContext.js'

export function ProfilePage() {
  const { currentUser, settings, stats, status, error } = useProfileContext()

  if (status !== 'success') {
    return <ProfileShell state={<ProfileState title={status === 'loading' ? 'Loading profile' : 'Could not load profile'} message={error} />} />
  }

  return (
    <ProfileShell>
      <AppPageHeader title="Profile" subtitle="Manage your account, stats, and player details." />
      <ProfileHero currentUser={currentUser} settings={settings} />
      <ProfileStats stats={stats} />
    </ProfileShell>
  )
}
