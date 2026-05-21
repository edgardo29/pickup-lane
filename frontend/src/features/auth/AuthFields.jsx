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
