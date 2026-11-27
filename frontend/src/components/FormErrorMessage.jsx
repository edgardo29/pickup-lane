import { AlertCircle } from 'lucide-react'

export function FormErrorMessage({ children, className = '', id }) {
  if (!children) {
    return null
  }

  const classes = ['form-error-message', className].filter(Boolean).join(' ')

  return (
    <p id={id} className={classes} role="alert">
      <AlertCircle aria-hidden="true" />
      <span>{children}</span>
    </p>
  )
}
