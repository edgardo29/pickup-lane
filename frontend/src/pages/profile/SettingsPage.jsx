import SettingsContent from './SettingsContent.jsx'
import { ProfileShell } from './ProfileShell.jsx'
import { ProfileState } from './ProfileState.jsx'
import { useSettingsPageModel } from './useSettingsPageModel.jsx'

export function SettingsPage() {
  const settingsPage = useSettingsPageModel()

  if (settingsPage.status !== 'success') {
    return (
      <ProfileShell
        state={
          <ProfileState
            title={settingsPage.status === 'loading' ? 'Loading settings' : 'Could not load settings'}
            message={settingsPage.error}
          />
        }
      />
    )
  }

  return <SettingsContent {...settingsPage} />
}
