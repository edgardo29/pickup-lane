import { AppPageShell } from '../../components/app/index.js'

export function ProfileShell({ children, state }) {
  return (
    <AppPageShell className="profile-page" mainClassName="profile-shell">
      {state || children}
    </AppPageShell>
  )
}
