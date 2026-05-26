import { useCallback, useEffect, useState } from 'react'
import {
  getNeedASubPost,
  listNeedASubPostRequests,
} from './needASubApi.js'

export function useNeedASubManageData({
  appUser,
  currentUser,
  postId,
}) {
  const [post, setPost] = useState(null)
  const [requests, setRequests] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  const loadManageView = useCallback(async () => {
    if (!currentUser) {
      setIsLoading(false)
      setError('Sign in to manage this post.')
      return
    }

    setIsLoading(true)
    setError('')

    try {
      const postResponse = await getNeedASubPost(postId, currentUser)
      setPost(postResponse)

      const isPostOwner = appUser?.id === postResponse.owner_user_id
      if (isPostOwner) {
        const requestResponse = await listNeedASubPostRequests(currentUser, postId)
        setRequests(requestResponse)
      } else {
        setRequests([])
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load post.')
    } finally {
      setIsLoading(false)
    }
  }, [appUser, currentUser, postId])

  useEffect(() => {
    const timerId = window.setTimeout(() => {
      loadManageView()
    }, 0)

    return () => window.clearTimeout(timerId)
  }, [loadManageView])

  return {
    error,
    isLoading,
    loadManageView,
    notice,
    post,
    requests,
    setError,
    setNotice,
    setPost,
  }
}
