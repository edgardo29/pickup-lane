import { sanitizeMoney } from './createGamePayment.js'

export function StepHeading({ title, text }) {
  return (
    <div className="create-game-heading">
      <h2>{title}</h2>
      <p>{text}</p>
    </div>
  )
}

export function SectionLabel({ children }) {
  return <h3 className="create-game-section-label">{children}</h3>
}

export function FormField({ icon, label, children }) {
  return (
    <div className="create-game-field">
      {icon}
      <span>{label}</span>
      {children}
    </div>
  )
}

export function TextInput({ form, updateField, field, label, placeholder }) {
  return (
    <label className="create-game-text-field">
      <span>{label}</span>
      <input
        placeholder={placeholder}
        value={form[field]}
        onChange={(event) => updateField(field, event.target.value)}
      />
    </label>
  )
}

export function SelectInput({ field, form, label, onChange, options, placeholder = 'Select', updateField }) {
  return (
    <label className="create-game-text-field create-game-text-field--select">
      <span>{label}</span>
      <select
        value={form[field]}
        onChange={(event) => {
          if (onChange) {
            onChange(event.target.value)
            return
          }

          updateField(field, event.target.value)
        }}
      >
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

export function StepperInput({ value, min, max, onChange }) {
  const numericValue = Number(value) || min

  function updateValue(nextValue) {
    onChange(Math.min(Math.max(nextValue, min), max))
  }

  return (
    <div className="create-game-stepper">
      <button type="button" onClick={() => updateValue(numericValue - 1)} aria-label="Decrease total spots">
        -
      </button>
      <strong>{numericValue}</strong>
      <button type="button" onClick={() => updateValue(numericValue + 1)} aria-label="Increase total spots">
        +
      </button>
    </div>
  )
}

export function CurrencyInput({ value, onChange }) {
  return (
    <div className="create-game-money-input">
      <span>$</span>
      <input
        inputMode="numeric"
        pattern="[0-9]*"
        value={value}
        onChange={(event) => onChange(sanitizeMoney(event.target.value))}
      />
    </div>
  )
}

export function TextareaInput({ form, updateField, field, label, maxLength, placeholder }) {
  return (
    <label className="create-game-textarea-field">
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

export function ReviewRow({ icon, label, value }) {
  return (
    <div className="create-game-review-row">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

export { PaymentMethodsEditor } from './CreateGamePaymentMethods.jsx'
export { DiscardModal } from './CreateGameDiscardModal.jsx'
