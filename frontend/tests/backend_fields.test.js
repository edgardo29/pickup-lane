// Proves the made-up answer check catches answers that differ from what the
// backend sends.

import { describe, expect, it } from 'vitest'
import { checkBackendAnswer } from './backendFields.js'

const ENDPOINT = 'GET /things'

const fields = {
  endpoints: { [ENDPOINT]: { $ref: '#/$defs/ThingList' } },
  $defs: {
    ThingList: {
      type: 'object',
      properties: { things: { type: 'array', items: { $ref: '#/$defs/Thing' } } },
      required: ['things'],
    },
    Thing: {
      type: 'object',
      properties: {
        id: { type: 'string', format: 'uuid' },
        count: { type: 'integer' },
        starts_at: { type: 'string', format: 'date-time' },
        note: { anyOf: [{ type: 'string' }, { type: 'null' }] },
        labels: { type: 'object', additionalProperties: { type: 'string' } },
      },
      required: ['id', 'count', 'starts_at', 'note', 'labels'],
    },
  },
}

function thing(overrides = {}) {
  return {
    id: '00000000-0000-4000-8000-000000000001',
    count: 3,
    starts_at: '2026-06-15T23:00:00Z',
    note: null,
    labels: {},
    ...overrides,
  }
}

function check(answer) {
  return () => checkBackendAnswer(fields, ENDPOINT, answer)
}

describe('made-up backend answer check', () => {
  it('accepts an answer that matches and leaves it unchanged', () => {
    const answer = { things: [thing({ note: 'Bring water' })] }
    const before = structuredClone(answer)

    expect(check(answer)).not.toThrow()
    expect(answer).toEqual(before)
  })

  it('rejects a missing field', () => {
    const withoutCount = thing()
    delete withoutCount.count

    expect(check({ things: [withoutCount] })).toThrow("must have required property 'count'")
  })

  it('rejects an extra field, even inside a list', () => {
    expect(check({ things: [thing({ price: '$10' })] })).toThrow(
      "/things/0: must NOT have additional properties ('price')",
    )
  })

  it('rejects the wrong kind of value', () => {
    expect(check({ things: [thing({ count: '3' })] })).toThrow('/things/0/count: must be integer')
  })

  it('rejects a value in the wrong format', () => {
    expect(check({ things: [thing({ id: 'thing-1' })] })).toThrow('must match format "uuid"')
    expect(check({ things: [thing({ starts_at: 'June 15' })] })).toThrow(
      'must match format "date-time"',
    )
  })

  it('keeps an object that accepts any keys open', () => {
    expect(check({ things: [thing({ labels: { color: 'blue', size: 'large' } })] })).not.toThrow()
    expect(check({ things: [thing({ labels: { size: 7 } })] })).toThrow('must be string')
  })

  it('names an endpoint that is missing from the fields file', () => {
    expect(() => checkBackendAnswer(fields, 'GET /other', {})).toThrow(
      'GET /other is not in this page\'s backend_fields.json',
    )
  })

  it('refuses combined shapes it cannot check correctly', () => {
    const combined = {
      endpoints: { [ENDPOINT]: { allOf: [{ $ref: '#/$defs/Thing' }] } },
      $defs: fields.$defs,
    }

    expect(() => checkBackendAnswer(combined, ENDPOINT, thing())).toThrow('uses "allOf"')
  })
})
