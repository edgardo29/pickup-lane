export const ACTIVE_ROSTER_STATUSES = new Set(['pending_payment', 'confirmed'])
export const ACTIVE_JOIN_STATUSES = new Set(['pending_payment', 'confirmed', 'waitlisted'])

export function getParticipantSummary(participants, totalSpots = 0) {
  const rosterParticipants = participants
    .filter((participant) => ACTIVE_ROSTER_STATUSES.has(participant.participant_status))
    .sort(
      (first, second) =>
        Number(first.roster_order || 999) - Number(second.roster_order || 999) ||
        first.display_name_snapshot.localeCompare(second.display_name_snapshot),
    )
  const waitlistParticipants = participants.filter(
    (participant) => participant.participant_status === 'waitlisted',
  )
  const roster = groupParticipantParties(rosterParticipants)
  const waitlist = groupParticipantParties(waitlistParticipants)
  const host = roster.find((participant) => participant.participant_type === 'host') || null
  const spotsLeft = Math.max((totalSpots || 0) - rosterParticipants.length, 0)

  return {
    host,
    roster,
    signedUpCount: rosterParticipants.length,
    spotsLeft,
    totalSpots: totalSpots || rosterParticipants.length,
    waitlist,
    waitlistCount: waitlistParticipants.length,
  }
}

export function getCurrentGuestCount(participants, currentParticipant, currentUserId) {
  if (!currentParticipant) {
    return 0
  }

  return participants.filter((participant) => {
    if (participant.participant_type !== 'guest' || !ACTIVE_JOIN_STATUSES.has(participant.participant_status)) {
      return false
    }

    if (currentParticipant.booking_id && participant.booking_id === currentParticipant.booking_id) {
      return true
    }

    return participant.guest_of_user_id === currentUserId
  }).length
}

export function buildChatSenderNames(participants) {
  return participants.reduce((names, participant) => {
    if (participant.user_id && participant.display_name_snapshot) {
      names.set(participant.user_id, participant.display_name_snapshot)
    }

    return names
  }, new Map())
}

function groupParticipantParties(participants) {
  const guestsByBookingId = new Map()
  const guestsByUserId = new Map()
  const visibleParticipants = []

  participants.forEach((participant) => {
    if (participant.participant_type === 'guest') {
      if (participant.booking_id) {
        const guests = guestsByBookingId.get(participant.booking_id) || []
        guests.push(participant)
        guestsByBookingId.set(participant.booking_id, guests)
      } else if (participant.guest_of_user_id) {
        const guests = guestsByUserId.get(participant.guest_of_user_id) || []
        guests.push(participant)
        guestsByUserId.set(participant.guest_of_user_id, guests)
      }

      return
    }

    visibleParticipants.push(participant)
  })

  return visibleParticipants.map((participant) => ({
    ...participant,
    guest_count: (
      (participant.booking_id ? guestsByBookingId.get(participant.booking_id)?.length || 0 : 0) +
      (participant.user_id ? guestsByUserId.get(participant.user_id)?.length || 0 : 0)
    ),
  }))
}
