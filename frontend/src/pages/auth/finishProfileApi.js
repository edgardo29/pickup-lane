import { apiRequest } from '../../lib/apiClient.js'

export function updateSignupProfile(userId, { dateOfBirth, firstName, lastName }) {
  return apiRequest(`/users/${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      date_of_birth: dateOfBirth,
      first_name: firstName,
      last_name: lastName,
    }),
  })
}
