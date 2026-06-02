import { AlertCircle } from 'lucide-react'

export function FormErrorMessage({ children, className = '' }) {
  if (!children) {
    return null
  }

  const classes = ['form-error-message', className].filter(Boolean).join(' ')

  return (
    <p className={classes} role="alert">
      <AlertCircle aria-hidden="true" />
      <span>{children}</span>
    </p>
  )
}
