import { MailIcon, SendIcon } from '../../components/AuthIcons.jsx'
import './EmailVerification.css'

export function EmailVerificationBlocker({ cooldownSeconds, error, notice, onSend, status }) {
  const isSending = status === 'sending'
  const buttonLabel = isSending ? 'Sending...' : cooldownSeconds > 0
    ? `Try again in ${cooldownSeconds}s` : status === 'sent'
      ? 'Resend verification email' : 'Send verification email'
  return (
    <section className="email-verification" aria-label="Email verification">
      <span className="email-verification__icon" aria-hidden="true"><MailIcon /></span>
      <div className="email-verification__copy">
        <h2>{status === 'sent' ? 'Check your email to continue.' : 'Verify your email to continue.'}</h2>
        <p role="status">{status === 'sent'
          ? 'We sent a verification link. Check your inbox or spam folder, then open the link to verify your account.'
          : 'Verify your account email before publishing a game or Sub Post.'}</p>
      </div>
      <div className="email-verification__actions">
        <button disabled={isSending || cooldownSeconds > 0} type="button" onClick={onSend}>
          <SendIcon aria-hidden="true" />{buttonLabel}
        </button>
        {notice && <p role="status">{notice}</p>}
        {error && <p role="alert">{error}</p>}
      </div>
    </section>
  )
}
