import { Link } from 'react-router-dom'
import {
  AppleIcon,
  GoogleIcon,
  LockIcon,
} from '../../components/AuthIcons.jsx'
import { monthOptions, securityText } from './authConstants.js'
import {
  getBirthYearOptions,
  getDaysInMonth,
  pad2,
} from './authHelpers.js'

export function AuthPanel({ children }) {
  return <section className="auth-panel">{children}</section>
}

export function AuthHeader({ title, subtitle }) {
  return (
    <header className="auth-header">
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </header>
  )
}

export function ProviderButtons({ disabled = false, onGoogle }) {
  return (
    <div className="auth-provider-grid">
      <button disabled={disabled} type="button" onClick={onGoogle}>
        <GoogleIcon />
        Continue with Google
      </button>
      <button disabled type="button" title="Apple sign-in will be added later.">
        <AppleIcon />
        Continue with Apple
      </button>
    </div>
  )
}

export function AuthField({
  action,
  hint,
  icon,
  label,
  placeholder,
  trailingAction,
  type = 'text',
  ...inputProps
}) {
  return (
    <label className="auth-field">
      <span className="auth-field__label">
        {label}
        {action}
      </span>
      <span className={`auth-field__input ${trailingAction ? 'auth-field__input--with-action' : ''}`}>
        {icon}
        <input {...inputProps} placeholder={placeholder} type={type} />
        {trailingAction}
      </span>
      {hint && <small>{hint}</small>}
    </label>
  )
}

export function BirthdayField({
  day,
  disabled,
  month,
  onDayChange,
  onMonthChange,
  onYearChange,
  year,
}) {
  const maxDay = getDaysInMonth(month, year)
  const dayOptions = Array.from({ length: maxDay }, (_, index) => pad2(index + 1))
  const yearOptions = getBirthYearOptions()

  function updateMonth(nextMonth) {
    onMonthChange(nextMonth)

    if (day && Number(day) > getDaysInMonth(nextMonth, year)) {
      onDayChange('')
    }
  }

  function updateYear(nextYear) {
    onYearChange(nextYear)

    if (day && Number(day) > getDaysInMonth(month, nextYear)) {
      onDayChange('')
    }
  }

  return (
    <fieldset className="auth-field auth-birthday-field" disabled={disabled}>
      <legend className="auth-field__label">Date of Birth</legend>
      <div className="auth-birthday-grid">
        <label className="auth-select-field">
          <span>Month</span>
          <select
            aria-label="Birth month"
            onChange={(event) => updateMonth(event.target.value)}
            value={month}
          >
            <option value="">Month</option>
            {monthOptions.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="auth-select-field">
          <span>Day</span>
          <select
            aria-label="Birth day"
            onChange={(event) => onDayChange(event.target.value)}
            value={day}
          >
            <option value="">Day</option>
            {dayOptions.map((value) => (
              <option key={value} value={value}>
                {Number(value)}
              </option>
            ))}
          </select>
        </label>
        <label className="auth-select-field">
          <span>Year</span>
          <select
            aria-label="Birth year"
            onChange={(event) => updateYear(event.target.value)}
            value={year}
          >
            <option value="">Year</option>
            {yearOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
      </div>
    </fieldset>
  )
}

export function PasswordVisibilityButton({ isVisible, onClick }) {
  return (
    <button
      aria-label={isVisible ? 'Hide password' : 'Show password'}
      className="auth-password-toggle"
      onClick={onClick}
      type="button"
    >
      {isVisible ? <EyeOffIcon /> : <EyeIcon />}
    </button>
  )
}

export function AuthHalo({ icon }) {
  return <div className="auth-halo">{icon}</div>
}

export function Divider({ label }) {
  return (
    <div className="auth-divider">
      <span />
      {label}
      <span />
    </div>
  )
}

export function AuthSwitch({ label, state, text, to }) {
  return (
    <p className="auth-switch">
      {text} <Link state={state} to={to}>{label}</Link>
    </p>
  )
}

export function SecurityNote() {
  return (
    <p className="auth-secure-note">
      <LockIcon />
      {securityText}
    </p>
  )
}

export function SecurityCallout({ icon, text, title }) {
  return (
    <div className="auth-security-callout">
      {icon}
      <p>
        <strong>{title}</strong>
        {text}
      </p>
    </div>
  )
}

export function AuthStep({ title, text }) {
  return (
    <div className="auth-step">
      <span aria-hidden="true" />
      <p>
        <strong>{title}</strong>
        {text}
      </p>
    </div>
  )
}

function EyeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

function EyeOffIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m3 3 18 18" />
      <path d="M10.6 10.6A3 3 0 0 0 12 15a3 3 0 0 0 2.4-1.2" />
      <path d="M9.9 5.2A10.8 10.8 0 0 1 12 5c6 0 9.5 7 9.5 7a14.2 14.2 0 0 1-2.7 3.4" />
      <path d="M6.6 6.6C3.9 8.2 2.5 12 2.5 12s3.5 7 9.5 7c1.6 0 3-.4 4.2-1" />
    </svg>
  )
}
