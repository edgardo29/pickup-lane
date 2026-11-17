// Checks a made-up backend answer against the fields the backend really sends.
//
// Each page folder has a backend_fields.json saved from the backend by
// `backend/.venv/bin/python -m backend.tests.frontend_fields.save` (run from the
// repository root). A missing field, an extra field, or a wrong kind of value
// fails the check.

import Ajv2020 from 'ajv/dist/2020.js'
import addFormats from 'ajv-formats'

const ajv = new Ajv2020({
  allErrors: true,
  // Never change an answer to make it pass. These are Ajv's defaults, kept
  // explicit on purpose.
  coerceTypes: false,
  removeAdditional: false,
  useDefaults: false,
})
addFormats(ajv)

const checksByFile = new WeakMap()

export function checkBackendAnswer(fieldsFile, endpoint, answer) {
  const check = checkFor(fieldsFile, endpoint)
  if (!check(answer)) {
    throw new Error(
      `Made-up ${endpoint} answer does not match backend_fields.json:\n${listProblems(check.errors)}`,
    )
  }
}

function checkFor(fieldsFile, endpoint) {
  if (!checksByFile.has(fieldsFile)) {
    checksByFile.set(fieldsFile, new Map())
  }
  const checks = checksByFile.get(fieldsFile)

  if (!checks.has(endpoint)) {
    if (!(endpoint in fieldsFile.endpoints)) {
      throw new Error(
        `${endpoint} is not in this page's backend_fields.json. Add it to PAGE_ENDPOINTS ` +
          'in backend/tests/frontend_fields/save.py and re-save.',
      )
    }
    const shape = structuredClone({ ...fieldsFile.endpoints[endpoint], $defs: fieldsFile.$defs })
    rejectExtraFields(shape)
    checks.set(endpoint, ajv.compile(shape))
  }
  return checks.get(endpoint)
}

// The backend's shapes allow extra fields unless they say otherwise. An object
// that lists its fields gets "no other fields allowed". An object that accepts
// any keys (it already says what extra keys may hold) stays as it is.
function rejectExtraFields(shape) {
  if (!shape || typeof shape !== 'object') {
    return
  }
  for (const keyword of ['allOf', 'not', 'if', 'dependentSchemas']) {
    if (keyword in shape) {
      throw new Error(
        `backend_fields.json uses "${keyword}". The extra-field check does not handle ` +
          'combined shapes yet; update rejectExtraFields in frontend/tests/backendFields.js.',
      )
    }
  }
  if (
    shape.properties &&
    !('additionalProperties' in shape) &&
    !('unevaluatedProperties' in shape)
  ) {
    shape.additionalProperties = false
  }

  for (const keyword of ['properties', 'patternProperties', '$defs']) {
    Object.values(shape[keyword] ?? {}).forEach(rejectExtraFields)
  }
  for (const keyword of ['anyOf', 'oneOf', 'prefixItems']) {
    ;(shape[keyword] ?? []).forEach(rejectExtraFields)
  }
  for (const keyword of ['items', 'additionalProperties', 'contains']) {
    rejectExtraFields(shape[keyword])
  }
}

function listProblems(errors) {
  return errors
    .map((error) => {
      const where = error.instancePath || '(top level)'
      const field = error.params.additionalProperty
      return `  ${where}: ${error.message}${field ? ` ('${field}')` : ''}`
    })
    .join('\n')
}
