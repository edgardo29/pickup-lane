import {
  getPaymentMethodLabel,
  paymentMethodOptions,
  sanitizeMoney,
} from './createGameUtils.js'

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

const MAX_PAYMENT_METHODS = 3

export function PaymentMethodsEditor({ allowNoPayment = false, methods, onChange }) {
  const safeMethods = Array.isArray(methods) && methods.length > 0
    ? methods
    : [{ type: 'venmo', value: '' }]
  const selectedTypes = new Set(safeMethods.map((method) => method.type))
  const canAddMethod = safeMethods.length < MAX_PAYMENT_METHODS && safeMethods[0]?.type !== 'none'

  function updateMethod(index, field, value) {
    if (field === 'type' && value === 'none') {
      onChange([{ type: 'none', value: '' }])
      return
    }

    onChange(
      safeMethods.map((method, methodIndex) => (
        methodIndex === index
          ? { ...method, [field]: value, value: field === 'type' ? '' : value }
          : method
      )),
    )
  }

  function addMethod() {
    const nextType = paymentMethodOptions.find((option) => (
      option.value !== 'none' && !selectedTypes.has(option.value)
    ))?.value || 'other'

    onChange([...safeMethods, { type: nextType, value: '' }])
  }

  function removeMethod(index) {
    const nextMethods = safeMethods.filter((_, methodIndex) => methodIndex !== index)
    onChange(nextMethods.length > 0 ? nextMethods : [{ type: 'venmo', value: '' }])
  }

  return (
    <div className="create-game-payment-methods">
      {safeMethods.map((method, index) => (
        <div className="create-game-payment-method-row" key={`${method.type}-${index}`}>
          <label>
            <span>Method</span>
            <select
              aria-label={`Payment method ${index + 1}`}
              value={method.type}
              onChange={(event) => updateMethod(index, 'type', event.target.value)}
            >
              {paymentMethodOptions
                .filter((option) => (
                  (allowNoPayment || option.value !== 'none') &&
                  (option.value === method.type || !selectedTypes.has(option.value))
                ))
                .map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
            </select>
          </label>
          {method.type === 'none' ? (
            <p className="create-game-payment-method-row__note">
              No player payment needed.
            </p>
          ) : (
            <>
              <label>
                <span>{getPaymentMethodLabel(method.type)} details</span>
                <input
                  placeholder="@username, phone, email, or note"
                  value={method.value}
                  onChange={(event) => updateMethod(index, 'value', event.target.value)}
                />
              </label>
              <button
                type="button"
                className="create-game-method-remove"
                aria-label={`Remove payment method ${index + 1}`}
                onClick={() => removeMethod(index)}
              >
                Remove
              </button>
            </>
          )}
        </div>
      ))}
      {canAddMethod && (
        <button className="create-game-secondary create-game-method-add" type="button" onClick={addMethod}>
          Add payment method
        </button>
      )}
    </div>
  )
}

export function DiscardModal({ onClose, onDiscard }) {
  return (
    <div className="create-game-modal-backdrop" role="presentation">
      <div className="create-game-modal" role="dialog" aria-modal="true" aria-labelledby="discard-game-title">
        <h2 id="discard-game-title">Discard game?</h2>
        <p>Your game has not been published. Any details you entered will be lost.</p>
        <div className="create-game-modal__actions">
          <button type="button" className="create-game-secondary" onClick={onClose}>
            Keep editing
          </button>
          <button type="button" className="create-game-danger" onClick={onDiscard}>
            Discard
          </button>
        </div>
      </div>
    </div>
  )
}
