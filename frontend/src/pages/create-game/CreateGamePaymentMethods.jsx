import { paymentMethodOptions } from './createGameData.js'
import { getPaymentMethodLabel } from './createGameFormatters.js'

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
