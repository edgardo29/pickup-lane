import { apiRequest } from '../../lib/apiClient.js'

export async function updateSignupProfile(firebaseUser, { dateOfBirth, firstName, lastName }) {
  if (!firebaseUser) {
    throw new Error('Sign in to finish your profile.')
  }

  return apiRequest('/users/me', {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${await firebaseUser.getIdToken()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      date_of_birth: dateOfBirth,
      first_name: firstName,
      last_name: lastName,
    }),
  })
}
