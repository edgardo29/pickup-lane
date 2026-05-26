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

export async function listUserPaymentMethods(firebaseUser) {
  return apiRequest('/user-payment-methods', {
    headers: await getPaymentAuthHeaders(firebaseUser),
  })
}

export async function createPaymentMethodSetupIntent(firebaseUser, setAsDefault = false) {
  return apiRequest('/user-payment-methods/setup-intent', {
    method: 'POST',
    headers: {
      ...(await getPaymentAuthHeaders(firebaseUser)),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ set_as_default: setAsDefault }),
  })
}

export async function syncPaymentMethod(firebaseUser, { setupIntentId, setAsDefault }) {
  return apiRequest('/user-payment-methods/sync', {
    method: 'POST',
    headers: {
      ...(await getPaymentAuthHeaders(firebaseUser)),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      setup_intent_id: setupIntentId,
      set_as_default: setAsDefault,
    }),
  })
}

export async function setDefaultPaymentMethod(firebaseUser, paymentMethodId) {
  return apiRequest(`/user-payment-methods/${paymentMethodId}/default`, {
    method: 'PATCH',
    headers: await getPaymentAuthHeaders(firebaseUser),
  })
}

export async function removePaymentMethod(firebaseUser, paymentMethodId) {
  return apiRequest(`/user-payment-methods/${paymentMethodId}`, {
    method: 'DELETE',
    headers: await getPaymentAuthHeaders(firebaseUser),
  })
}
