import assert from 'node:assert/strict'
import test from 'node:test'

import { selectAdminActionPrimaryTarget } from '../../src/pages/admin/audit/adminAuditLogTargets.js'

test('selectAdminActionPrimaryTarget uses list target while detail is loading', () => {
  const listPrimaryTarget = {
    label: 'Old list target',
    target_id: 'list-target',
  }

  assert.equal(
    selectAdminActionPrimaryTarget({ listPrimaryTarget }),
    listPrimaryTarget,
  )
})

test('selectAdminActionPrimaryTarget prefers fresh detail primary target', () => {
  const listPrimaryTarget = {
    label: 'Old list target',
    target_id: 'list-target',
  }
  const detailPrimaryTarget = {
    is_primary: true,
    label: 'Fresh detail target',
    target_id: 'detail-target',
  }

  assert.equal(
    selectAdminActionPrimaryTarget({
      detailTargets: [
        {
          is_primary: false,
          label: 'Additional target',
          target_id: 'additional-target',
        },
        detailPrimaryTarget,
      ],
      listPrimaryTarget,
    }),
    detailPrimaryTarget,
  )
})
