import { EyeIcon, EyeOffIcon } from './ProfileIcons.jsx'

export function PasswordField({
  label,
  onChange,
  onToggleVisibility,
  showPassword,
  value,
}) {
  return (
    <label className="profile-edit-field settings-password-field">
      <span>{label}</span>
      <span className="settings-password-field__input">
        <input
          autoComplete="new-password"
          onChange={(event) => onChange(event.target.value)}
          type={showPassword ? 'text' : 'password'}
          value={value}
        />
        <button
          aria-label={showPassword ? 'Hide password' : 'Show password'}
          onClick={onToggleVisibility}
          type="button"
        >
          {showPassword ? <EyeOffIcon /> : <EyeIcon />}
        </button>
      </span>
    </label>
  )
}

export function ProfileEditField({ label, onChange, required = false, type = 'text', ...inputProps }) {
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
