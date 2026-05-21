export function EmailVerificationBlocker({ cooldownSeconds, error, notice, onSend, status }) {
  const isSending = status === 'sending'
  const isCoolingDown = cooldownSeconds > 0
  const buttonLabel = isSending
    ? 'Sending...'
    : isCoolingDown
      ? `Try again in ${cooldownSeconds}s`
      : status === 'sent'
        ? 'Resend verification email'
        : 'Send verification email'

  return (
    <section className="create-game-blocker">
      <div>
        <p>{status === 'sent' ? 'Email verification sent' : 'Email verification required'}</p>
        <h2>{status === 'sent' ? 'Check your email to continue.' : 'Verify your email to become a host.'}</h2>
        <span>
          {status === 'sent'
            ? 'We sent a verification link to your email. Check your inbox or spam folder, then open the link to verify your account.'
            : 'Before you can publish a community game, we need to confirm your email address. This helps keep host accounts real and protects players from fake listings.'}
        </span>
      </div>
      <div className="create-game-blocker__actions">
        <button
          className="create-game-primary"
          disabled={isSending || isCoolingDown}
          type="button"
          onClick={onSend}
        >
          {buttonLabel}
        </button>
        {notice && <strong className="create-game-blocker__notice">{notice}</strong>}
        {error && <strong className="create-game-blocker__error">{error}</strong>}
      </div>
    </section>
  )
}
