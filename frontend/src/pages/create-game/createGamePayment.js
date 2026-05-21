import { defaultPaymentMethods } from './createGameData.js'

export function getPriceCents(form) {
  return Number(form.price) * 100
}

export function normalizePaymentMethods(paymentMethods) {
  if (!Array.isArray(paymentMethods) || paymentMethods.length === 0) {
    return defaultPaymentMethods
  }

  const normalizedMethods = paymentMethods
    .filter((method) => method && typeof method === 'object')
    .map((method) => ({
      type: typeof method.type === 'string' ? method.type : 'other',
      value: typeof method.value === 'string' ? method.value : '',
    }))

  return normalizedMethods.length > 0 ? normalizedMethods : defaultPaymentMethods
}

export function sanitizeMoney(value) {
  const digitsOnly = value.replace(/[^\d]/g, '')
  if (!digitsOnly) {
    return 0
  }

  return Math.min(Number(digitsOnly), 999)
}

export function serializePaymentMethods(paymentMethods) {
  if (!Array.isArray(paymentMethods)) {
    return []
  }

  return paymentMethods
    .filter((method) => method && typeof method === 'object')
    .map((method) => ({
      type: typeof method.type === 'string' && method.type ? method.type : 'other',
      value: method.type === 'cash'
        ? String(method.value || 'Cash').trim()
        : String(method.value || '').trim(),
    }))
    .filter((method) => method.type !== 'none' && method.value)
}
