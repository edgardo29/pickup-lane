import { useEffect, useMemo, useState } from 'react'
import { buildRequestGroups } from './needASubSelectors.js'

export function useNeedASubRequestGroups({ post, requests }) {
  const [selectedPositionId, setSelectedPositionId] = useState('')
  const [activeRequestStatus, setActiveRequestStatus] = useState('pending')
  const [waitlistModalGroup, setWaitlistModalGroup] = useState(null)

  const requestGroups = useMemo(
    () => buildRequestGroups(post, requests),
    [post?.positions, requests],
  )
  const defaultRequestGroup = useMemo(
    () => requestGroups.find((group) => group.pending.length > 0) || requestGroups[0] || null,
    [requestGroups],
  )
  const selectedGroup = useMemo(
    () =>
      requestGroups.find((group) => group.position.id === selectedPositionId)
      || defaultRequestGroup
      || null,
    [defaultRequestGroup, requestGroups, selectedPositionId],
  )

  useEffect(() => {
    if (!requestGroups.length) {
      setSelectedPositionId('')
      return
    }

    if (!requestGroups.some((group) => group.position.id === selectedPositionId)) {
      setSelectedPositionId(defaultRequestGroup?.position.id || requestGroups[0].position.id)
    }
  }, [defaultRequestGroup, requestGroups, selectedPositionId])

  return {
    activeRequestStatus,
    requestGroups,
    selectedGroup,
    setActiveRequestStatus,
    setSelectedPositionId,
    setWaitlistModalGroup,
    waitlistModalGroup,
  }
}
