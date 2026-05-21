export function NeedASubFormField({ children, className = '', label }) {
  return (
    <label className={`need-sub-field ${className}`.trim()}>
      <span>{label}</span>
      {children}
    </label>
  )
}
