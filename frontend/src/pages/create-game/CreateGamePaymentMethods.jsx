import { useState } from 'react'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import {
  MAX_HOST_PAYMENT_METHODS,
  paymentMethodOptions,
} from './createGameData.js'
import { getPaymentMethodLabel } from './createGameFormatters.js'
import { getIncompletePaymentMethod } from './createGamePayment.js'

export function PaymentMethodsEditor({ allowNoPayment = false, methods, onChange }) {
  const [methodError, setMethodError] = useState('')
  const fallbackMethods = allowNoPayment
    ? [{ type: 'none', value: '' }]
    : [{ type: 'venmo', value: '' }]
  const safeMethods = (
    Array.isArray(methods) && methods.length > 0
      ? methods
      : fallbackMethods
  ).slice(0, MAX_HOST_PAYMENT_METHODS)
  const selectedTypes = new Set(safeMethods.map((method) => method.type))
  const canAddMethod = safeMethods.length < MAX_HOST_PAYMENT_METHODS && safeMethods[0]?.type !== 'none'

  function updateMethod(index, field, value) {
    setMethodError('')

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
    const incompleteMethod = getIncompletePaymentMethod(safeMethods)

    if (incompleteMethod) {
      setMethodError(`Add ${getPaymentMethodLabel(incompleteMethod.type)} details before adding another payment method.`)
      return
    }

    const nextType = paymentMethodOptions.find((option) => (
      option.value !== 'none' && !selectedTypes.has(option.value)
    ))?.value || 'other'

    onChange([...safeMethods, { type: nextType, value: '' }])
  }

  function removeMethod(index) {
    setMethodError('')
    const nextMethods = safeMethods.filter((_, methodIndex) => methodIndex !== index)
    onChange(nextMethods.length > 0 ? nextMethods : [{ type: 'venmo', value: '' }])
  }

  return (
    <div className="create-game-payment-methods">
      <div className="create-game-payment-methods__header">
        <h3>Payment methods <span>(how players pay you directly)</span></h3>
        <button
          className="create-game-method-add"
          disabled={!canAddMethod}
          type="button"
          aria-label="Add payment method"
          title="Add payment method"
          onClick={addMethod}
        >
          + Add Method
        </button>
      </div>

      <FormErrorMessage className="create-game-payment-methods__error">
        {methodError}
      </FormErrorMessage>

      <div className="create-game-payment-methods__grid">
        {safeMethods.map((method, index) => (
          <div
            className="create-game-payment-method-row"
            key={`${method.type}-${index}`}
          >
            <label className="create-game-payment-method-row__method">
              <span>Method</span>
              <span className="create-game-select-control">
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
                <span className="create-game-select-control__chevron" aria-hidden="true" />
              </span>
            </label>
            {method.type === 'none' ? (
              <div className="create-game-payment-method-row__details create-game-payment-method-row__details--static">
                <span>Details</span>
                <p className="create-game-payment-method-row__note">
                  No player payment needed.
                </p>
              </div>
            ) : (
              <>
                <label className="create-game-payment-method-row__details">
                  <span>{getPaymentMethodLabel(method.type)} details</span>
                  <input
                    value={method.value}
                    onChange={(event) => updateMethod(index, 'value', event.target.value)}
                  />
                </label>
                {index > 0 && (
                  <button
                    type="button"
                    className="create-game-method-remove"
                    aria-label={`Remove payment method ${index + 1}`}
                    title="Remove payment method"
                    onClick={() => removeMethod(index)}
                  >
                    <span aria-hidden="true" />
                  </button>
                )}
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
