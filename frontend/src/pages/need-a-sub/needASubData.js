export { US_STATE_OPTIONS } from '../../data/usStates.js'

export const FORMAT_OPTIONS = ['3v3', '4v4', '5v5', '6v6', '7v7', '8v8', '9v9', '10v10', '11v11']

export const SKILL_OPTIONS = [
  { label: 'Any Skill', value: 'any' },
  { label: 'Beginner', value: 'beginner' },
  { label: 'Recreational', value: 'recreational' },
  { label: 'Intermediate', value: 'intermediate' },
  { label: 'Advanced', value: 'advanced' },
  { label: 'Competitive', value: 'competitive' },
]

export const ENVIRONMENT_OPTIONS = [
  { label: 'Indoor', value: 'indoor' },
  { label: 'Outdoor', value: 'outdoor' },
]

export const GROUP_OPTIONS = [
  { label: 'Men', value: 'men' },
  { label: 'Women', value: 'women' },
  { label: 'Coed', value: 'coed' },
]

export const POSITION_OPTIONS = [
  { label: 'Field Player', value: 'field_player' },
  { label: 'Goalkeeper', value: 'goalkeeper' },
]

export const MAX_SUB_ROWS = 6
export const MAX_TOTAL_SUBS = 11
export const MAX_WAITLIST_REQUESTS_PER_POST = 25
export const needASubFieldLimits = {
  locationName: 60,
  addressLine1: 80,
  city: 50,
  postalCode: 10,
  neighborhood: 40,
  priceDue: 8,
  notes: 500,
}

export const POST_TABS = [
  { key: 'all', label: 'All Posts' },
  { key: 'mine', label: 'My Posts' },
]

export function buildInitialNeedASubForm() {
  return {
    date: getDefaultDate(),
    startTime: '19:00',
    endTime: '21:00',
    formatLabel: '',
    environment: '',
    skillLevel: '',
    gamePlayerGroup: '',
    locationName: '',
    addressLine1: '',
    city: '',
    state: '',
    postalCode: '',
    neighborhood: '',
    priceDue: '',
    notes: '',
    positions: getDefaultPositions('coed'),
  }
}

export const TIME_OPTIONS = buildTimeOptions()
export const MIN_DATE_VALUE = toDateInputValue(new Date())

export function getDefaultDate() {
  const date = new Date()
  date.setDate(date.getDate() + 3)
  return toDateInputValue(date)
}

export function toDateInputValue(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function buildTimeOptions() {
  const options = []
  for (let hour = 5; hour <= 23; hour += 1) {
    for (let minute = 0; minute < 60; minute += 5) {
      const value = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`
      const date = new Date(`2026-01-01T${value}:00`)
      options.push({
        value,
        label: new Intl.DateTimeFormat('en-US', {
          hour: 'numeric',
          minute: '2-digit',
        }).format(date),
      })
    }
  }
  return options
}

export function getDefaultPositionGroup(postGroup) {
  if (postGroup === 'men') {
    return 'men'
  }
  if (postGroup === 'women') {
    return 'women'
  }
  return 'open'
}

export function getDefaultPositions(postGroup) {
  return [
    {
      position_label: 'field_player',
      player_group: getDefaultPositionGroup(postGroup),
      spots_needed: 1,
      sort_order: 0,
    },
  ]
}

export function getPositionGroupOptions(postGroup) {
  if (postGroup === 'men') {
    return [{ label: 'Men', value: 'men' }]
  }

  if (postGroup === 'women') {
    return [{ label: 'Women', value: 'women' }]
  }

  return [
    { label: 'Any Player', value: 'open' },
    { label: 'Men', value: 'men' },
    { label: 'Women', value: 'women' },
  ]
}

export function getMaxPositionRows(postGroup) {
  return POSITION_OPTIONS.length * getPositionGroupOptions(postGroup).length
}

export function getNextPosition(positions, postGroup) {
  const usedPairs = new Set(
    positions.map((position) => `${position.position_label}:${position.player_group}`),
  )
  const groups = getPositionGroupOptions(postGroup).map((option) => option.value)

  for (const position of POSITION_OPTIONS) {
    for (const group of groups) {
      if (!usedPairs.has(`${position.value}:${group}`)) {
        return {
          position_label: position.value,
          player_group: group,
        }
      }
    }
  }

  return {
    position_label: 'field_player',
    player_group: getDefaultPositionGroup(postGroup),
  }
}
