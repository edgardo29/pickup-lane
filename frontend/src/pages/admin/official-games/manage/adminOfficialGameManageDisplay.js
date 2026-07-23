const auditRelatedTargetFields = [
  ['target_user_id', 'User'],
  ['target_booking_id', 'Booking'],
  ['target_participant_id', 'Participant'],
  ['target_payment_id', 'Payment'],
  ['target_refund_id', 'Refund'],
  ['target_game_credit_id', 'Credit'],
  ['target_venue_id', 'Venue'],
  ['target_venue_image_id', 'Venue image'],
  ['target_message_id', 'Message'],
  ['target_sub_post_id', 'Need a Sub post'],
  ['target_sub_post_request_id', 'Need a Sub request'],
  ['target_sub_post_position_id', 'Need a Sub position'],
  ['target_sub_chat_message_id', 'Need a Sub chat message'],
  ['target_notification_id', 'Notification'],
  ['target_platform_notice_campaign_id', 'Platform notice campaign'],
  ['target_support_flag_id', 'Support flag'],
  ['target_money_issue_id', 'Money Issue'],
  ['target_admin_action_id', 'Audit action'],
]

export function formatAdminDateTime(value) {
  if (!value) {
    return 'Not set'
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function getStatusLabel(value) {
  return String(value || 'unknown').replaceAll('_', ' ')
}

export function getTitleLabel(value) {
  return getStatusLabel(value)
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function getParticipantUserLabel(userId, participants) {
  const participant = participants.find(
    (item) => item.user_id === userId && item.participant_type !== 'guest',
  )

  return participant?.display_name_snapshot || `User ${String(userId).slice(0, 8)}`
}

export function getBookingBuyerLabel(booking, participants) {
  const bookingParticipants = participants.filter(
    (participant) => participant.booking_id === booking.id,
  )
  const buyerParticipant = bookingParticipants.find(
    (participant) => participant.user_id === booking.buyer_user_id,
  )
  const firstParticipant = bookingParticipants.find(
    (participant) => participant.display_name_snapshot,
  )

  return (
    buyerParticipant?.display_name_snapshot
    || firstParticipant?.display_name_snapshot
    || `User ${String(booking.buyer_user_id).slice(0, 8)}`
  )
}

export function getWaitlistUserLabel(entry, participants) {
  const userParticipants = participants.filter(
    (participant) =>
      participant.user_id === entry.user_id
      && participant.display_name_snapshot,
  )
  const promotedParticipant = entry.promoted_booking_id
    ? userParticipants.find(
      (participant) => participant.booking_id === entry.promoted_booking_id,
    )
    : null
  const waitlistedParticipant = userParticipants.find(
    (participant) => participant.participant_status === 'waitlisted',
  )

  return (
    promotedParticipant?.display_name_snapshot
    || waitlistedParticipant?.display_name_snapshot
    || userParticipants[0]?.display_name_snapshot
    || `User ${String(entry.user_id).slice(0, 8)}`
  )
}

export function getWaitlistTimelineLabel(entry) {
  if (entry.cancelled_at) {
    return `Cancelled ${formatAdminDateTime(entry.cancelled_at)}`
  }
  if (entry.expired_at) {
    return `Expired ${formatAdminDateTime(entry.expired_at)}`
  }
  if (entry.promoted_at) {
    return `Promoted ${formatAdminDateTime(entry.promoted_at)}`
  }
  return `Joined ${formatAdminDateTime(entry.joined_at)}`
}

export function getPaymentTimelineLabel(payment) {
  if (payment.paid_at) {
    return `Paid ${formatAdminDateTime(payment.paid_at)}`
  }
  if (payment.failure_code || payment.failure_message) {
    return 'Failure recorded'
  }
  return `Created ${formatAdminDateTime(payment.created_at)}`
}

export function getRefundTimelineLabel(refund) {
  if (refund.refunded_at) {
    return `Refunded ${formatAdminDateTime(refund.refunded_at)}`
  }
  if (refund.approved_at) {
    return `Approved ${formatAdminDateTime(refund.approved_at)}`
  }
  return `Requested ${formatAdminDateTime(refund.requested_at)}`
}

export function getCreditUsageTimelineLabel(usage) {
  if (usage.released_at) {
    return `Released ${formatAdminDateTime(usage.released_at)}`
  }
  if (usage.redeemed_at) {
    return `Redeemed ${formatAdminDateTime(usage.redeemed_at)}`
  }
  if (usage.reserved_at) {
    return `Reserved ${formatAdminDateTime(usage.reserved_at)}`
  }
  return `Created ${formatAdminDateTime(usage.created_at)}`
}

export function getPrimaryGameChat(chatRooms) {
  return chatRooms.find((chatRoom) => chatRoom.chat_status === 'active') || chatRooms[0] || null
}

export function getChatSenderLabel(message, participants) {
  if (message.message_type === 'system' || message.message_type === 'pinned_update') {
    return 'Pickup Lane'
  }

  const participant = participants.find(
    (item) => item.user_id === message.sender_user_id && item.display_name_snapshot,
  )
  if (participant) {
    return participant.display_name_snapshot
  }

  return message.sender_user_id
    ? `User ${String(message.sender_user_id).slice(0, 8)}`
    : 'Unknown sender'
}

export function getChatMessageTimelineLabel(message) {
  if (message.removed_at) {
    return `Removed ${formatAdminDateTime(message.removed_at)}`
  }
  return `Sent ${formatAdminDateTime(message.created_at)}`
}

export function getAuditRelatedTargetLabel(action) {
  const relatedTarget = auditRelatedTargetFields.find(([field]) => Boolean(action[field]))
  if (!relatedTarget) {
    return 'Game'
  }

  const [field, label] = relatedTarget
  return `${label} ${String(action[field]).slice(0, 8)}`
}
