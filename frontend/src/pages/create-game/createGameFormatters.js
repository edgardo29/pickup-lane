import {
  paymentMethodOptions,
  playerGroupOptions,
  skillLevelOptions,
} from './createGameData.js'
import { serializePaymentMethods } from './createGamePayment.js'
import { formatTime } from './createGameSchedule.js'

export { formatTime }

export function buildAddress(form) {
  const stateLine = [form.state.trim(), form.zip.trim()].filter(Boolean).join(' ')
  const cityLine = [form.city.trim(), stateLine].filter(Boolean).join(', ')
  return [form.street.trim(), cityLine].filter(Boolean).join(' · ')
}

export function buildPreviewLocation(form) {
  return buildAddress(form) || form.neighborhood.trim() || 'Address not set'
}

export function buildReview(form) {
  return {
    date: new Intl.DateTimeFormat('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(new Date(`${form.date}T12:00:00`)),
    time: `${formatTime(form.startTime)} - ${formatTime(form.endTime)}`,
  }
}

export function capitalize(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : ''
}

export function formatGamePlayerGroup(value) {
  return playerGroupOptions.find((option) => option.value === value)?.label || capitalize(value) || 'Player group not set'
}

export function formatSkillLevel(value) {
  return skillLevelOptions.find((option) => option.value === value)?.label || capitalize(value) || 'Skill not set'
}

export function formatHostPaymentMethods(paymentMethods) {
  const methods = serializePaymentMethods(paymentMethods)

  if (methods.length === 0) {
    return 'Not added'
  }

  return methods
    .map((method) => {
      const label = getPaymentMethodLabel(method.type)
      return `${label}: ${method.value}`
    })
    .join(', ')
}

export function formatMoney(cents) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format((cents || 0) / 100)
}

export function getPaymentMethodLabel(value) {
  return paymentMethodOptions.find((option) => option.value === value)?.label || 'Other'
}
