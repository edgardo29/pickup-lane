import { Link } from 'react-router-dom'

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
