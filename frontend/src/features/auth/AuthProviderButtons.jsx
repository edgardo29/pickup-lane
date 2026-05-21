import {
  AppleIcon,
  GoogleIcon,
} from '../../components/AuthIcons.jsx'

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
