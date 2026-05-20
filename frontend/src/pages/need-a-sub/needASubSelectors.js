export const ACTIVE_REQUEST_STATUSES = ['pending', 'confirmed', 'sub_waitlist']

export function countHeldSpots(position) {
  return Number(position.pending_count || 0) + Number(position.confirmed_count || 0)
}

export function getSpotsLeft(post) {
  const positionTotal = (post.positions || []).reduce((sum, position) => {
    const spotsLeft = Number(position.spots_needed || 0) - countHeldSpots(position)
    return sum + Math.max(0, spotsLeft)
  }, 0)

  if (post.positions?.length) {
    return positionTotal
  }

  return Math.max(0, Number(post.subs_needed || 0) - Number(post.confirmed_count || 0))
}

export function getActiveRequestForPost(myRequests, postId) {
  return myRequests.find(
    (request) =>
      request.sub_post_id === postId && ACTIVE_REQUEST_STATUSES.includes(request.request_status),
  )
}

export function buildRequestGroups(post, requests) {
  return (post?.positions || []).map((position, index) => {
    const positionRequests = requests.filter(
      (request) => request.sub_post_position_id === position.id,
    )
    const pending = positionRequests.filter((request) => request.request_status === 'pending')
    const confirmed = positionRequests.filter((request) => request.request_status === 'confirmed')
    const waitlisted = positionRequests.filter(
      (request) => request.request_status === 'sub_waitlist',
    )

    return {
      position,
      label: `Sub need ${index + 1}`,
      pending,
      confirmed,
      waitlisted,
    }
  })
}

export function summarizeRequestGroups(post, requestGroups) {
  const totalNeeded = (post?.positions || []).reduce(
    (sum, position) => sum + Number(position.spots_needed || 0),
    0,
  )
  const confirmed = requestGroups.reduce((sum, group) => sum + group.confirmed.length, 0)
  const pending = requestGroups.reduce((sum, group) => sum + group.pending.length, 0)
  const waitlisted = requestGroups.reduce((sum, group) => sum + group.waitlisted.length, 0)

  return {
    confirmed,
    needed: totalNeeded,
    open: Math.max(0, totalNeeded - confirmed),
    pending,
    waitlisted,
  }
}
