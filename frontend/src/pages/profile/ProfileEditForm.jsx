import { useMemo, useState } from 'react'
import { InitialsAvatar } from './ProfileAvatar.jsx'
import { ProfileEditField } from './ProfileFields.jsx'
import { saveUserSettings, updateProfileUser } from './profileApi.js'

export function ProfileEditForm({
  currentUser,
  firebaseUser,
  onCancel,
  onSaved,
  settings,
}) {
  const [formEdits, setFormEdits] = useState({})
  const [saveStatus, setSaveStatus] = useState('idle')
  const [saveError, setSaveError] = useState('')

  const loadedForm = useMemo(() => {
    if (!currentUser) {
      return null
    }

    return {
      email: currentUser.email || '',
      first_name: currentUser.first_name || '',
      home_city: currentUser.home_city || settings.selected_city || '',
      home_state: currentUser.home_state || settings.selected_state || '',
      last_name: currentUser.last_name || '',
      phone: currentUser.phone || '',
    }
  }, [currentUser, settings])

  const form = loadedForm ? { ...loadedForm, ...formEdits } : null

  if (!form) {
    return null
  }

  const updateField = (field, value) => {
    setFormEdits((currentEdits) => ({ ...currentEdits, [field]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSaveStatus('saving')
    setSaveError('')

    const trimmedForm = Object.fromEntries(
      Object.entries(form).map(([field, value]) => [field, value.trim()]),
    )

    try {
      const profilePayload = {
        email: trimmedForm.email,
        first_name: trimmedForm.first_name,
        home_city: trimmedForm.home_city || null,
        home_state: trimmedForm.home_state || null,
        last_name: trimmedForm.last_name,
        phone: trimmedForm.phone,
      }

      const savedUser = await updateProfileUser(firebaseUser, profilePayload)

      const settingsPayload = {
        selected_city: trimmedForm.home_city || null,
        selected_state: trimmedForm.home_state || null,
      }

      const savedSettings = await saveUserSettings(firebaseUser, settingsPayload)

      onSaved({
        currentUser: {
          ...currentUser,
          ...(savedUser || {}),
          ...profilePayload,
        },
        settings: {
          ...settings,
          ...(savedSettings || {}),
          ...settingsPayload,
        },
      })
    } catch (requestError) {
      setSaveError(
        requestError instanceof Error ? requestError.message : 'Unable to save profile.',
      )
      setSaveStatus('idle')
    }
  }

  return (
    <form className="profile-edit-card" onSubmit={handleSubmit}>
      <div className="profile-edit-card__intro">
        <InitialsAvatar user={{ first_name: form.first_name, last_name: form.last_name }} />
        <div>
          <h2>{`${form.first_name} ${form.last_name}`.trim() || 'Player'}</h2>
        </div>
      </div>

      <div className="profile-edit-grid">
        <ProfileEditField
          label="First name"
          required
          value={form.first_name}
          onChange={(value) => updateField('first_name', value)}
        />
        <ProfileEditField
          label="Last name"
          required
          value={form.last_name}
          onChange={(value) => updateField('last_name', value)}
        />
        <ProfileEditField
          label="Email"
          required
          type="email"
          value={form.email}
          onChange={(value) => updateField('email', value)}
        />
        <ProfileEditField
          label="Phone"
          required
          type="tel"
          value={form.phone}
          onChange={(value) => updateField('phone', value)}
        />
        <ProfileEditField
          label="Home city"
          value={form.home_city}
          onChange={(value) => updateField('home_city', value)}
        />
        <ProfileEditField
          label="Home state"
          maxLength={2}
          value={form.home_state}
          onChange={(value) => updateField('home_state', value.toUpperCase())}
        />
      </div>

      {saveError && <p className="profile-edit-error">{saveError}</p>}

      <div className="profile-edit-actions">
        <button className="profile-edit-cancel" onClick={onCancel} type="button">
          Back
        </button>
        <button className="profile-primary-action" disabled={saveStatus === 'saving'} type="submit">
          {saveStatus === 'saving' ? 'Saving...' : 'Save changes'}
        </button>
      </div>
    </form>
  )
}
