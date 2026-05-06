import { Link, useNavigate } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import BrowseAppNav from '../components/BrowseAppNav.jsx'
import {
  CalendarIcon,
  MapPinIcon,
  ShieldCheckIcon,
  SoccerBallIcon,
  UserIcon,
} from '../components/BrowseIcons.jsx'
import { apiRequest } from '../lib/apiClient.js'
import '../styles/profile-settings.css'

const DEMO_CURRENT_USER_AUTH_ID = 'demo-current-user'

const emptyStats = {
  games_played_count: 0,
  games_hosted_completed_count: 0,
  no_show_count: 0,
  late_cancel_count: 0,
  host_cancel_count: 0,
}

const emptySettings = {
  push_notifications_enabled: true,
  email_notifications_enabled: true,
  sms_notifications_enabled: false,
  marketing_opt_in: false,
  location_permission_status: 'unknown',
  selected_city: '',
  selected_state: '',
}

export function ProfilePage() {
  const { currentUser, settings, stats, status, error } = useProfileContext()

  if (status !== 'success') {
    return <ProfileShell state={<ProfileState title={status === 'loading' ? 'Loading profile' : 'Could not load profile'} message={error} />} />
  }

  const statCards = [
    {
      icon: <SoccerBallIcon />,
      label: 'Games Played',
      meta: 'All time',
      value: stats.games_played_count,
    },
    {
      icon: <ShoeIcon />,
      label: 'Hosted Completed',
      meta: 'All time',
      value: stats.games_hosted_completed_count,
    },
    {
      icon: <NoShowIcon />,
      label: 'No-Shows',
      meta: 'Last 90 days',
      value: stats.no_show_count,
    },
    {
      icon: <ClockAlertIcon />,
      label: 'Late Cancels',
      meta: 'Last 90 days',
      value: stats.late_cancel_count,
    },
  ]

  return (
    <ProfileShell>
      <section className="profile-hero-card">
        <InitialsAvatar user={currentUser} size="large" />

        <div className="profile-hero-card__body">
          <div className="profile-hero-card__top">
            <div>
              <p className="profile-kicker">Player Profile</p>
              <h1>{getFullName(currentUser)}</h1>
            </div>

            <Link className="profile-icon-button" to="/settings" aria-label="Open settings">
              <GearIcon />
            </Link>
          </div>

          <div className="profile-meta">
            <span>
              <MapPinIcon />
              {formatLocation(currentUser, settings)}
            </span>
            <span>
              <CalendarIcon />
              Member since {formatMemberSince(currentUser.member_since)}
            </span>
          </div>

          <Link className="profile-secondary-action" to="/profile/edit">
            <PencilIcon />
            Edit profile
          </Link>
        </div>
      </section>

      <section className="profile-stat-grid" aria-label="Player stats">
        {statCards.map((item) => (
          <article className="profile-stat-card" key={item.label}>
            <span className="profile-stat-card__icon">{item.icon}</span>
            <div>
              <h2>{item.label}</h2>
              <p>{item.meta}</p>
            </div>
            <strong>{item.value}</strong>
          </article>
        ))}
      </section>
    </ProfileShell>
  )
}

export function EditProfilePage() {
  const navigate = useNavigate()
  const { currentUser, settings, status, error } = useProfileContext()
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

  if (status !== 'success') {
    return <ProfileShell state={<ProfileState title={status === 'loading' ? 'Loading profile' : 'Could not load profile'} message={error} />} />
  }

  if (!form) {
    return <ProfileShell state={<ProfileState title="Preparing profile" />} />
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
      await apiRequest(`/users/${currentUser.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: trimmedForm.email,
          first_name: trimmedForm.first_name,
          home_city: trimmedForm.home_city || null,
          home_state: trimmedForm.home_state || null,
          last_name: trimmedForm.last_name,
          phone: trimmedForm.phone,
        }),
      })

      await saveUserSettings(currentUser.id, settings, {
        selected_city: trimmedForm.home_city || null,
        selected_state: trimmedForm.home_state || null,
      })

      navigate('/profile')
    } catch (requestError) {
      setSaveError(
        requestError instanceof Error ? requestError.message : 'Unable to save profile.',
      )
      setSaveStatus('idle')
    }
  }

  return (
    <ProfileShell>
      <section className="profile-edit-layout">
        <div className="settings-heading">
          <Link className="settings-back-link" to="/profile">
            Back to profile
          </Link>
          <p className="profile-kicker">Profile</p>
          <h1>Edit profile</h1>
        </div>

        <form className="profile-edit-card" onSubmit={handleSubmit}>
          <div className="profile-edit-card__intro">
            <InitialsAvatar user={{ first_name: form.first_name, last_name: form.last_name }} />
            <div>
              <h2>{`${form.first_name} ${form.last_name}`.trim() || 'Player'}</h2>
              <p>Update the account details players and hosts see around the app.</p>
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
            <Link className="profile-edit-cancel" to="/profile">
              Cancel
            </Link>
            <button className="profile-primary-action" disabled={saveStatus === 'saving'} type="submit">
              {saveStatus === 'saving' ? 'Saving...' : 'Save changes'}
            </button>
          </div>
        </form>
      </section>
    </ProfileShell>
  )
}

export function SettingsPage() {
  const { currentUser, settings, paymentMethods, status, error } = useProfileContext()

  if (status !== 'success') {
    return <ProfileShell state={<ProfileState title={status === 'loading' ? 'Loading settings' : 'Could not load settings'} message={error} />} />
  }

  const notificationSummary = getNotificationSummary(settings)
  const defaultPaymentMethod =
    paymentMethods.find((method) => method.is_default) || paymentMethods[0] || null

  const preferenceRows = [
    {
      icon: <BellIcon />,
      title: 'Notifications',
      text: notificationSummary,
    },
    {
      icon: <PaymentCardIcon />,
      title: 'Payment Methods',
      text: defaultPaymentMethod
        ? `${capitalize(defaultPaymentMethod.card_brand)} ending ${defaultPaymentMethod.card_last4}`
        : 'No card on file',
    },
    {
      icon: <HelpIcon />,
      title: 'Help & Support',
      text: 'FAQ, support, and contact us',
    },
    {
      icon: <DocumentIcon />,
      title: 'Terms & Conditions',
      text: 'Read our terms of service',
    },
    {
      icon: <ShieldCheckIcon />,
      title: 'Privacy Policy',
      text: 'How we handle your data',
    },
  ]

  const accountRows = [
    {
      icon: <LogoutIcon />,
      title: 'Log Out',
      text: 'Sign out after auth is connected',
    },
    {
      icon: <TrashIcon />,
      title: 'Delete Account',
      text: 'Permanently delete your account',
      tone: 'danger',
    },
  ]

  return (
    <ProfileShell>
      <section className="settings-layout">
        <div className="settings-main">
          <div className="settings-heading">
            <Link className="settings-back-link" to="/profile">
              Back to profile
            </Link>
            <p className="profile-kicker">Account</p>
            <h1>Settings</h1>
          </div>

          <Link className="settings-account-row" to="/profile">
            <InitialsAvatar user={currentUser} />
            <div>
              <strong>{getFullName(currentUser)}</strong>
              <span>{currentUser.email}</span>
            </div>
            <ChevronRightIcon />
          </Link>

          <SettingsGroup title="Preferences & Account" rows={preferenceRows} />
          <SettingsGroup title="Account" rows={accountRows} />
        </div>

        <aside className="settings-summary-card">
          <InitialsAvatar user={currentUser} />
          <h2>{getFullName(currentUser)}</h2>
          <p>{formatLocation(currentUser, settings)}</p>

          <div className="settings-summary-card__items">
            <span>
              <strong>{capitalize(currentUser.account_status)}</strong>
              Account status
            </span>
            <span>
              <strong>{formatMemberSince(currentUser.member_since)}</strong>
              Member since
            </span>
          </div>
        </aside>
      </section>
    </ProfileShell>
  )
}

function ProfileEditField({ label, onChange, required = false, type = 'text', ...inputProps }) {
  return (
    <label className="profile-edit-field">
      <span>{label}</span>
      <input
        {...inputProps}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        type={type}
      />
    </label>
  )
}

function ProfileShell({ children, state }) {
  return (
    <div className="profile-page">
      <BrowseAppNav />
      <main className="profile-shell">{state || children}</main>
    </div>
  )
}

async function saveUserSettings(userId, currentSettings, nextSettings) {
  try {
    return await apiRequest(`/user-settings/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(nextSettings),
    })
  } catch (requestError) {
    if (
      requestError instanceof Error &&
      !requestError.message.toLowerCase().includes('not found')
    ) {
      throw requestError
    }

    return apiRequest('/user-settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email_notifications_enabled: currentSettings.email_notifications_enabled,
        location_permission_status: currentSettings.location_permission_status,
        marketing_opt_in: currentSettings.marketing_opt_in,
        push_notifications_enabled: currentSettings.push_notifications_enabled,
        sms_notifications_enabled: currentSettings.sms_notifications_enabled,
        user_id: userId,
        ...nextSettings,
      }),
    })
  }
}

function SettingsGroup({ title, rows }) {
  return (
    <section className="settings-group">
      <h2>{title}</h2>
      <div className="settings-group__rows">
        {rows.map((row) => (
          <button
            className={`settings-row ${row.tone === 'danger' ? 'settings-row--danger' : ''}`}
            key={row.title}
            type="button"
          >
            <span className="settings-row__icon">{row.icon}</span>
            <span>
              <strong>{row.title}</strong>
              <small>{row.text}</small>
            </span>
            <ChevronRightIcon />
          </button>
        ))}
      </div>
    </section>
  )
}

function ProfileState({ title, message }) {
  return (
    <section className="profile-state">
      <UserIcon />
      <h1>{title}</h1>
      {message && <p>{message}</p>}
    </section>
  )
}

function InitialsAvatar({ user, size = 'default' }) {
  return (
    <div className={`profile-avatar profile-avatar--${size}`} aria-hidden="true">
      {getInitials(user)}
    </div>
  )
}

function useProfileContext() {
  const [currentUser, setCurrentUser] = useState(null)
  const [settings, setSettings] = useState(emptySettings)
  const [stats, setStats] = useState(emptyStats)
  const [paymentMethods, setPaymentMethods] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    let ignore = false

    async function loadProfileContext() {
      setStatus('loading')
      setError('')

      try {
        const users = await apiRequest('/users')
        const demoUser = users.find((user) => user.auth_user_id === DEMO_CURRENT_USER_AUTH_ID)

        if (!demoUser) {
          throw new Error('Demo signed-in user was not found. Rerun the demo seed.')
        }

        const [settingsResponse, statsResponse, paymentMethodsResponse] = await Promise.all([
          apiRequest(`/user-settings/${demoUser.id}`).catch(() => emptySettings),
          apiRequest(`/user-stats/${demoUser.id}`).catch(() => emptyStats),
          apiRequest(`/user-payment-methods?user_id=${demoUser.id}`).catch(() => []),
        ])

        if (!ignore) {
          setCurrentUser(demoUser)
          setSettings(settingsResponse)
          setStats(statsResponse)
          setPaymentMethods(paymentMethodsResponse)
          setStatus('success')
        }
      } catch (requestError) {
        if (!ignore) {
          setError(requestError instanceof Error ? requestError.message : 'Unable to load profile.')
          setStatus('error')
        }
      }
    }

    loadProfileContext()

    return () => {
      ignore = true
    }
  }, [])

  return useMemo(
    () => ({ currentUser, error, paymentMethods, settings, stats, status }),
    [currentUser, error, paymentMethods, settings, stats, status],
  )
}

function getFullName(user) {
  return `${user?.first_name || ''} ${user?.last_name || ''}`.trim() || 'Player'
}

function getInitials(user) {
  const first = user?.first_name?.[0] || 'P'
  const last = user?.last_name?.[0] || 'L'
  return `${first}${last}`.toUpperCase()
}

function formatLocation(user, settings) {
  const city = settings.selected_city || user.home_city || 'Chicago'
  const state = settings.selected_state || user.home_state || 'IL'
  return [city, state].filter(Boolean).join(', ')
}

function formatMemberSince(value) {
  if (!value) {
    return 'Recently'
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    year: 'numeric',
  }).format(new Date(value))
}

function getNotificationSummary(settings) {
  const enabled = [
    settings.push_notifications_enabled ? 'push' : '',
    settings.email_notifications_enabled ? 'email' : '',
    settings.sms_notifications_enabled ? 'SMS' : '',
  ].filter(Boolean)

  return enabled.length ? `${enabled.join(', ')} enabled` : 'Notifications are off'
}

function capitalize(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : ''
}

function GearIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="3.4" />
      <path d="M19.4 13.7a7.8 7.8 0 0 0 .1-1.7l2-1.5-2-3.5-2.4 1a7.3 7.3 0 0 0-1.4-.8L15.4 4h-4l-.4 3.2c-.5.2-1 .5-1.4.8l-2.4-1-2 3.5 2 1.5a7.8 7.8 0 0 0 .1 1.7l-2 1.5 2 3.5 2.4-1c.4.3.9.6 1.4.8l.4 3.2h4l.4-3.2c.5-.2 1-.5 1.4-.8l2.4 1 2-3.5Z" />
    </svg>
  )
}

function PencilIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m4.5 16.8-.8 3.5 3.5-.8L18.8 8 16 5.2Z" />
      <path d="m14.8 6.4 2.8 2.8" />
    </svg>
  )
}

function BellIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M18 10.5a6 6 0 0 0-12 0v3.8L4.5 17h15L18 14.3Z" />
      <path d="M9.5 19.2a2.8 2.8 0 0 0 5 0" />
    </svg>
  )
}

function PaymentCardIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="3.5" y="5.5" width="17" height="13" rx="2" />
      <path d="M3.5 9h17" />
      <path d="M7 15h3" />
    </svg>
  )
}

function HelpIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M9.6 9.3A2.6 2.6 0 0 1 12 7.8c1.5 0 2.7 1 2.7 2.4 0 1.2-.7 1.8-1.7 2.4-.8.5-1 .9-1 1.7" />
      <path d="M12 17h.1" />
    </svg>
  )
}

function DocumentIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 3.5h9l3 3v14H6Z" />
      <path d="M15 3.5v3h3" />
      <path d="M9 11h6" />
      <path d="M9 15h5" />
    </svg>
  )
}

function LogoutIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M13 5H6.5v14H13" />
      <path d="M12 12h8" />
      <path d="m17 8 4 4-4 4" />
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4.5 6.5h15" />
      <path d="M9 6.5V4h6v2.5" />
      <path d="M7 8.8 8 20h8l1-11.2" />
      <path d="M10.2 11.5v5" />
      <path d="M13.8 11.5v5" />
    </svg>
  )
}

function ShoeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 14.8c2 .7 3.5.7 5.5-.2l1.7 2.2h5.5c1.5 0 2.8 1 3.1 2.4H6.8c-2.3 0-3.8-1.2-4-3.2Z" />
      <path d="m10.5 14.6 1-5.1" />
      <path d="M13.3 16.8 15 12" />
      <path d="M16.6 16.8 18 13.4" />
    </svg>
  )
}

function NoShowIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="10" cy="7.8" r="3.1" />
      <path d="M3.5 19c.5-3.6 2.7-5.4 6.5-5.4 1.2 0 2.2.2 3.1.6" />
      <circle cx="17" cy="17" r="4" />
      <path d="m15.5 15.5 3 3" />
      <path d="m18.5 15.5-3 3" />
    </svg>
  )
}

function ClockAlertIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 1.8" />
      <path d="M12 17h.1" />
    </svg>
  )
}

function ChevronRightIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m9 6 6 6-6 6" />
    </svg>
  )
}
