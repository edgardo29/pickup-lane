export function formatAdminMoney(cents, currency = 'USD') {
  const numericCents = Number(cents || 0)
  const wholeCurrencyUnit = Number.isInteger(numericCents) && numericCents % 100 === 0

  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: currency || 'USD',
    minimumFractionDigits: wholeCurrencyUnit ? 0 : 2,
    maximumFractionDigits: wholeCurrencyUnit ? 0 : 2,
  }).format(numericCents / 100)
}
