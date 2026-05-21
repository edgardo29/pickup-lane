import { AppPageShell } from '../../components/app/index.js'

export function ProfileShell({ children, state }) {
  return (
    <AppPageShell className="profile-page" mainClassName="app-page-shell--narrow profile-shell">
      {state || children}
    </AppPageShell>
  )
}
