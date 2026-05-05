import { Link } from 'react-router-dom'
import BrandMark from '../components/BrandMark.jsx'
import {
  ArrowLeftIcon,
  AppleIcon,
  CalendarIcon,
  CheckEmailIcon,
  GoogleIcon,
  InfoIcon,
  LockIcon,
  MailIcon,
  SendIcon,
  ShieldCheckIcon,
  UserIcon,
} from '../components/AuthIcons.jsx'
import '../styles/auth.css'

const securityText = 'Your information is secure and will never be shared.'

export function SignInPage() {
  return (
    <AuthShell
      eyebrow="Welcome back"
      title="Sign in to Pickup Lane"
      subtitle="Jump back into your games, messages, and saved spots."
      variant="wide"
    >
      <AuthPanel>
        <AuthHeader title="Welcome back" subtitle="Sign in to your Pickup Lane account." />

        <ProviderButtons />

        <Divider label="or sign in with email" />

        <form className="auth-form">
          <AuthField
            icon={<MailIcon />}
            label="Email"
            placeholder="Enter your email"
            type="email"
          />

          <AuthField
            action={<Link to="/forgot-password">Forgot?</Link>}
            icon={<LockIcon />}
            label="Password"
            placeholder="Enter your password"
            type="password"
          />

          <button className="auth-primary-button auth-primary-button--muted" type="button">
            Sign In
          </button>
        </form>

        <AuthSwitch text="Don’t have an account?" to="/create-account" label="Create Account" />
      </AuthPanel>
    </AuthShell>
  )
}

export function CreateAccountPage() {
  return (
    <AuthShell
      eyebrow="Create account"
      title="Start playing faster"
      subtitle="Use social sign-in or create a Pickup Lane account with email."
      variant="wide"
    >
      <AuthPanel>
        <AuthHeader title="Create Account" subtitle="Create your Pickup Lane account to get started." />

        <ProviderButtons />

        <Divider label="or create with email" />

        <form className="auth-form">
          <AuthField
            icon={<MailIcon />}
            label="Email"
            placeholder="Enter your email"
            type="email"
          />

          <AuthField
            hint="At least 8 characters with a number or symbol"
            icon={<LockIcon />}
            label="Password"
            placeholder="Create a password"
            type="password"
          />

          <Link className="auth-primary-button" to="/finish-profile">
            Create Account
          </Link>
        </form>

        <AuthSwitch text="Already have an account?" to="/sign-in" label="Sign In" />

        <p className="auth-terms">
          By creating an account, you agree to our <a href="#terms">Terms of Service</a> and{' '}
          <a href="#privacy">Privacy Policy</a>.
        </p>
      </AuthPanel>
    </AuthShell>
  )
}

export function FinishProfilePage() {
  return (
    <AuthShell
      eyebrow="Profile setup"
      title="Finish your player profile"
      subtitle="A few details help us keep games organized and age appropriate."
    >
      <AuthPanel>
        <BackLink />
        <AuthHeader
          title="Finish Profile"
          subtitle="Just a few details to finish setting up your account."
        />

        <form className="auth-form">
          <div className="auth-two-column">
            <AuthField icon={<UserIcon />} label="First Name" placeholder="First name" />
            <AuthField icon={<UserIcon />} label="Last Name" placeholder="Last name" />
          </div>

          <AuthField
            icon={<CalendarIcon />}
            label="Date of Birth"
            placeholder="MM / DD / YYYY"
            type="text"
          />

          <p className="auth-inline-note">
            <InfoIcon />
            You must be at least 13 years old to use Pickup Lane.
          </p>

          <button className="auth-primary-button" type="button">
            Continue
          </button>
        </form>

        <SecurityNote />
      </AuthPanel>
    </AuthShell>
  )
}

export function ForgotPasswordPage() {
  return (
    <AuthShell
      eyebrow="Password help"
      title="Reset access securely"
      subtitle="Send a password reset link and get back to your games."
    >
      <AuthPanel>
        <BackLink />
        <AuthHalo icon={<LockIcon />} />
        <AuthHeader
          title="Forgot Password?"
          subtitle="No worries. Enter your email and we’ll send you a link to reset your password."
        />

        <form className="auth-form">
          <AuthField
            icon={<MailIcon />}
            label="Email"
            placeholder="Enter your email"
            type="email"
          />

          <Link className="auth-primary-button" to="/check-email">
            <SendIcon />
            Send Reset Link
          </Link>
        </form>

        <SecurityCallout
          icon={<ShieldCheckIcon />}
          title="Secure reset"
          text="For your security, we’ll send a private reset link that expires automatically."
        />
      </AuthPanel>
    </AuthShell>
  )
}

export function CheckEmailPage() {
  return (
    <AuthShell
      eyebrow="Reset sent"
      title="Check your email"
      subtitle="Your reset link is on the way. Keep this page handy in case you need another one."
    >
      <AuthPanel>
        <BackLink />
        <AuthHalo icon={<CheckEmailIcon />} />
        <AuthHeader
          title="Check your email"
          subtitle={
            <>
              We sent a password reset link to <strong>alex@email.com</strong>
            </>
          }
        />

        <div className="auth-steps">
          <AuthStep
            title="It may take a few minutes to arrive."
            text="Check your inbox and spam folder."
          />
          <AuthStep title="Click the link in the email" text="to reset your password." />
          <AuthStep title="The link will expire in 60 minutes" text="for your security." />
        </div>

        <div className="auth-resend-card">
          <MailIcon />
          <span>Resend email</span>
          <strong>00:48</strong>
        </div>

        <Link className="auth-text-link" to="/forgot-password">
          Didn’t receive the email?
        </Link>

        <Link className="auth-primary-button" to="/sign-in">
          Back to Sign In
        </Link>
      </AuthPanel>
    </AuthShell>
  )
}

function AuthShell({ children, variant = 'default' }) {
  return (
    <main className={`auth-page auth-page--${variant}`}>
      <Link className="auth-home-link" to="/">
        <ArrowLeftIcon />
        Home
      </Link>

      <div className="auth-frame">
        <Link className="auth-frame__brand" to="/" aria-label="Pickup Lane home">
          <BrandMark compact />
        </Link>

        {children}
      </div>
    </main>
  )
}

function AuthPanel({ children }) {
  return <section className="auth-panel">{children}</section>
}

function AuthHeader({ title, subtitle }) {
  return (
    <header className="auth-header">
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </header>
  )
}

function ProviderButtons() {
  return (
    <div className="auth-provider-grid">
      <button type="button">
        <GoogleIcon />
        Continue with Google
      </button>
      <button type="button">
        <AppleIcon />
        Continue with Apple
      </button>
    </div>
  )
}

function AuthField({ action, hint, icon, label, placeholder, type = 'text' }) {
  return (
    <label className="auth-field">
      <span className="auth-field__label">
        {label}
        {action}
      </span>
      <span className="auth-field__input">
        {icon}
        <input placeholder={placeholder} type={type} />
      </span>
      {hint && <small>{hint}</small>}
    </label>
  )
}

function AuthHalo({ icon }) {
  return <div className="auth-halo">{icon}</div>
}

function BackLink() {
  return (
    <Link className="auth-back-link" to="/sign-in" aria-label="Back to sign in">
      <ArrowLeftIcon />
    </Link>
  )
}

function Divider({ label }) {
  return (
    <div className="auth-divider">
      <span />
      {label}
      <span />
    </div>
  )
}

function AuthSwitch({ label, text, to }) {
  return (
    <p className="auth-switch">
      {text} <Link to={to}>{label}</Link>
    </p>
  )
}

function SecurityNote() {
  return (
    <p className="auth-secure-note">
      <LockIcon />
      {securityText}
    </p>
  )
}

function SecurityCallout({ icon, text, title }) {
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

function AuthStep({ title, text }) {
  return (
    <div className="auth-step">
      <span />
      <p>
        <strong>{title}</strong>
        {text}
      </p>
    </div>
  )
}
