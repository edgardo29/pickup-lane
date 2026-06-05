export const createSubPostSteps = [
  { key: 'game', label: 'Game' },
  { key: 'subs', label: 'Subs' },
  { key: 'location', label: 'Location' },
  { key: 'notes', label: 'Notes' },
  { key: 'review', label: 'Review & Publish', mobileLabel: 'Review' },
]

export const editSubPostSteps = [
  { key: 'game', label: 'Game' },
  { key: 'subs', label: 'Subs' },
  { key: 'location', label: 'Location' },
  { key: 'notes', label: 'Notes' },
  { key: 'review', label: 'Review & Save', mobileLabel: 'Review' },
]

export function getSubPostFlowSteps(mode = 'create') {
  return mode === 'edit' ? editSubPostSteps : createSubPostSteps
}
