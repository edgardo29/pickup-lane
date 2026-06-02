import { formatTime, getDefaultDate } from './createGameSchedule.js'

export { US_STATE_OPTIONS } from '../../data/usStates.js'

export const COMMUNITY_PUBLISH_FEE_CENTS = 499
export const MAX_HOST_PAYMENT_METHODS = 2
export const MAX_TOTAL_SPOTS = 99
export const MINIMUM_TOTAL_SPOTS = 6

export const createGameFieldLimits = {
  venueName: 60,
  street: 80,
  city: 50,
  zip: 10,
  neighborhood: 40,
  parkingNote: 120,
  gameNotes: 200,
  hostRules: 200,
}

export const formatOptions = ['3v3', '4v4', '5v5', '6v6', '7v7', '8v8', '9v9', '10v10', '11v11']

export const playerGroupOptions = [
  { label: 'Coed', value: 'coed' },
  { label: 'Men', value: 'men' },
  { label: 'Women', value: 'women' },
]

export const skillLevelOptions = [
  { label: 'Any Skill', value: 'any' },
  { label: 'Beginner', value: 'beginner' },
  { label: 'Recreational', value: 'recreational' },
  { label: 'Intermediate', value: 'intermediate' },
  { label: 'Advanced', value: 'advanced' },
  { label: 'Competitive', value: 'competitive' },
]

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
  { id: 1, label: 'Game' },
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
  format: '',
  gamePlayerGroup: '',
  skillLevel: '',
  environment: '',
  totalSpots: '',
  price: 0,
  venueName: '',
  street: '',
  city: '',
  state: '',
  zip: '',
  neighborhood: '',
  parkingNote: '',
  gameNotes: '',
  hostRules: '',
  paymentMethods: [{ type: 'none', value: '' }],
}
