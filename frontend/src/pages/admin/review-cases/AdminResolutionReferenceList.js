import React from 'react'

const REFERENCE_PRESENTATION = {
  finding: {
    identityField: 'content_moderation_finding_id',
    label: 'Finding',
  },
  signal: {
    identityField: 'signal_id',
    label: 'Chat signal',
  },
  enforcement_action: {
    identityField: 'admin_action_id',
    label: 'Enforcement action',
  },
  source_case: {
    identityField: 'source_case_id',
    label: 'Merged source case',
  },
}

export function AdminResolutionReferenceList({ references = [] }) {
  if (!references.length) return null

  return React.createElement(
    'ul',
    { className: 'admin-review-resolution-references' },
    references.map((reference) => {
      const presentation = REFERENCE_PRESENTATION[reference.reference_type]
      const identity = presentation
        ? reference[presentation.identityField]
        : null
      const currentState = ['finding', 'signal'].includes(reference.reference_type)
        ? (reference.was_current ? 'Current at resolution' : 'Historical at resolution')
        : null

      return React.createElement(
        'li',
        {
          'data-reference-type': reference.reference_type,
          key: reference.id,
        },
        React.createElement('span', null, presentation?.label || 'Reference'),
        React.createElement('code', null, identity || 'Unavailable'),
        currentState ? React.createElement('span', null, currentState) : null,
      )
    }),
  )
}
