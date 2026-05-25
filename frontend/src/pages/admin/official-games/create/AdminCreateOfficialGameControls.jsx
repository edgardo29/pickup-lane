export function AdminCreateStepHeading({ title, text }) {
  return (
    <div className="admin-create-heading">
      <h2>{title}</h2>
      <p>{text}</p>
    </div>
  )
}

export function AdminCreateSectionLabel({ children }) {
  return <h3 className="admin-create-section-label">{children}</h3>
}

export function AdminCreateField({ icon, label, children }) {
  return (
    <div className="admin-create-field">
      {icon}
      <span>{label}</span>
      {children}
    </div>
  )
}

export function AdminCreateStepperInput({ ariaLabel, value, min, max, onChange }) {
  const numericValue = Number(value) || min

  function updateValue(nextValue) {
    onChange(Math.min(Math.max(nextValue, min), max))
  }

  return (
    <div className="admin-create-stepper">
      <button type="button" onClick={() => updateValue(numericValue - 1)} aria-label={`Decrease ${ariaLabel}`}>
        -
      </button>
      <strong>{numericValue}</strong>
      <button type="button" onClick={() => updateValue(numericValue + 1)} aria-label={`Increase ${ariaLabel}`}>
        +
      </button>
    </div>
  )
}

export function AdminCreateCurrencyInput({ value, onChange }) {
  function sanitizeMoney(nextValue) {
    const digitsOnly = nextValue.replace(/[^\d]/g, '')
    onChange(digitsOnly ? Math.min(Number(digitsOnly), 999) : 0)
  }

  return (
    <div className="admin-create-money-input">
      <span>$</span>
      <input
        inputMode="numeric"
        pattern="[0-9]*"
        value={value}
        onChange={(event) => sanitizeMoney(event.target.value)}
      />
    </div>
  )
}

export function AdminCreateTextInput({ field, form, label, placeholder, updateField }) {
  return (
    <label className="admin-create-text-field">
      <span>{label}</span>
      <input
        placeholder={placeholder}
        value={form[field]}
        onChange={(event) => updateField(field, event.target.value)}
      />
    </label>
  )
}

export function AdminCreateSelectInput({
  field,
  form,
  label,
  options,
  placeholder = 'Select',
  updateField,
}) {
  return (
    <label className="admin-create-text-field">
      <span>{label}</span>
      <select value={form[field]} onChange={(event) => updateField(field, event.target.value)}>
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}

export function AdminCreateToggle({ checked, label, text, onChange }) {
  return (
    <label className="admin-create-check-field">
      <input checked={checked} type="checkbox" onChange={(event) => onChange(event.target.checked)} />
      <span />
      <strong>{label}</strong>
      {text && <small>{text}</small>}
    </label>
  )
}

export function AdminCreateModeButton({ active, children, onClick }) {
  return (
    <button className={active ? 'active' : ''} type="button" onClick={onClick}>
      {children}
    </button>
  )
}

export function AdminCreateTextarea({ field, form, label, maxLength, placeholder, updateField }) {
  return (
    <label className="admin-create-textarea-field">
      <span>{label}</span>
      <textarea
        maxLength={maxLength}
        placeholder={placeholder}
        value={form[field]}
        onChange={(event) => updateField(field, event.target.value)}
      />
      <small>{form[field].length}/{maxLength}</small>
    </label>
  )
}

export function AdminCreateReviewRow({ icon, label, value }) {
  return (
    <div className="admin-create-review-row">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}
