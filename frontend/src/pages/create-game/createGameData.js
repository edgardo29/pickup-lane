import { formatTime, getDefaultDate } from './createGameSchedule.js'

export { US_STATE_OPTIONS } from '../../data/usStates.js'

export const COMMUNITY_PUBLISH_FEE_CENTS = 499
export const MINIMUM_TOTAL_SPOTS = 6

export const formatOptions = ['3v3', '4v4', '5v5', '6v6', '7v7', '8v8', '9v9', '10v10', '11v11']

export const environmentOptions = [
  { label: 'Indoor', value: 'indoor' },
  { label: 'Outdoor', value: 'outdoor' },
]

export const timeOptions = Array.from({ length: 24 * 12 }, (_, index) => {
  const totalMinutes = index * 5
  const hours = String(Math.floor(totalMinutes / 60)).padStart(2, '0')
  const minutes = String(totalMinutes % 60).padStart(2, '0')
  const value = `${hours}:${minutes}`

  return {
    label: formatTime(value),
    value,
  }
})

export const steps = [
  { id: 1, label: 'Basics' },
  { id: 2, label: 'Location' },
  { id: 3, label: 'Notes' },
  { id: 4, label: 'Review & Publish' },
]

export const paymentMethodOptions = [
  { label: 'None', value: 'none' },
  { label: 'Venmo', value: 'venmo' },
  { label: 'Zelle', value: 'zelle' },
  { label: 'Cash App', value: 'cash_app' },
  { label: 'PayPal', value: 'paypal' },
  { label: 'Apple Cash', value: 'apple_cash' },
  { label: 'Cash', value: 'cash' },
  { label: 'Other', value: 'other' },
]

export const defaultPaymentMethods = [{ type: 'venmo', value: '' }]

export const initialForm = {
  date: getDefaultDate(),
  startTime: '18:00',
  endTime: '20:00',
  format: '7v7',
  environment: 'outdoor',
  totalSpots: 14,
  price: 25,
  venueName: '',
  street: '',
  city: '',
  state: '',
  zip: '',
  neighborhood: '',
  parkingNote: '',
  gameNotes: '',
  paymentMethods: defaultPaymentMethods,
}
