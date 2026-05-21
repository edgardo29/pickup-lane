import { LockIcon } from '../../components/AuthIcons.jsx'
import { securityText } from './authConstants.js'

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
