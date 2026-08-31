import { apiRequest } from './apiClient.js'

export async function getPaymentAuthHeaders(firebaseUser) {
  if (!firebaseUser) {
    throw new Error('Sign in to manage payment methods.')
  }

  const token = await firebaseUser.getIdToken()
  return {
    Authorization: `Bearer ${token}`,
  }
}

export function createPaymentMethodOperationId() {
  if (!globalThis.crypto?.randomUUID) {
    throw new Error('Payment-method operation ids are not supported in this browser.')
  }

  return globalThis.crypto.randomUUID()
}

export function buildIdempotencyHeaders(operationId) {
  const normalizedOperationId = typeof operationId === 'string' ? operationId.trim() : ''
  if (!normalizedOperationId) {
    throw new Error('Payment-method operation id is required.')
  }

  return { 'Idempotency-Key': normalizedOperationId }
}

export async function listUserPaymentMethods(firebaseUser) {
  return apiRequest('/user-payment-methods', {
    headers: await getPaymentAuthHeaders(firebaseUser),
  })
}

export async function createPaymentMethodSetupIntent(firebaseUser, setAsDefault = false, operationId) {
  return apiRequest('/user-payment-methods/setup-intent', {
    method: 'POST',
    headers: {
      ...(await getPaymentAuthHeaders(firebaseUser)),
      'Content-Type': 'application/json',
      ...buildIdempotencyHeaders(operationId),
    },
    body: JSON.stringify({ set_as_default: setAsDefault }),
  })
}

export async function syncPaymentMethod(firebaseUser, { setupIntentId, setAsDefault, operationId }) {
  return apiRequest('/user-payment-methods/sync', {
    method: 'POST',
    headers: {
      ...(await getPaymentAuthHeaders(firebaseUser)),
      'Content-Type': 'application/json',
      ...buildIdempotencyHeaders(operationId),
    },
    body: JSON.stringify({
      setup_intent_id: setupIntentId,
      set_as_default: setAsDefault,
    }),
  })
}

export async function setDefaultPaymentMethod(firebaseUser, paymentMethodId, operationId) {
  return apiRequest(`/user-payment-methods/${paymentMethodId}/default`, {
    method: 'PATCH',
    headers: {
      ...(await getPaymentAuthHeaders(firebaseUser)),
      ...buildIdempotencyHeaders(operationId),
    },
  })
}

export async function removePaymentMethod(firebaseUser, paymentMethodId, operationId) {
  return apiRequest(`/user-payment-methods/${paymentMethodId}`, {
    method: 'DELETE',
    headers: {
      ...(await getPaymentAuthHeaders(firebaseUser)),
      ...buildIdempotencyHeaders(operationId),
    },
  })
}
