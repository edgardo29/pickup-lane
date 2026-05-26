export function isPaymentMethodExpired(method, now = new Date()) {
  if (!method?.exp_month || !method?.exp_year) {
    return false
  }

  const currentMonth = now.getMonth() + 1
  const currentYear = now.getFullYear()

  return (
    Number(method.exp_year) < currentYear ||
    (Number(method.exp_year) === currentYear && Number(method.exp_month) < currentMonth)
  )
}

export function getUsablePaymentMethods(paymentMethods, now = new Date()) {
  return paymentMethods.filter((method) => !isPaymentMethodExpired(method, now))
}

export function getPreferredPaymentMethod(paymentMethods, now = new Date()) {
  const usableMethods = getUsablePaymentMethods(paymentMethods, now)
  return usableMethods.find((method) => method.is_default) || usableMethods[0] || null
}

export function formatPaymentMethodExpiration(method) {
  return `${String(method.exp_month).padStart(2, '0')}/${method.exp_year}`
}
