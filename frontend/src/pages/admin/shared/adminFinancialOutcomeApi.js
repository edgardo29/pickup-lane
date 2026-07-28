import { apiRequest } from '../../../lib/apiClient.js'
import { getAdminHeaders } from './adminApi.js'

export async function getAdminFinancialOutcome({
  financialOutcomeId,
  firebaseUser,
}) {
  return apiRequest(`/admin/money/financial-outcomes/${financialOutcomeId}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function createAdminFinancialOutcome({
  firebaseUser,
  payload,
}) {
  return apiRequest('/admin/money/financial-outcomes', {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify(payload),
  })
}
