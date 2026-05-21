import { useCallback, useEffect, useState } from 'react'
import {
  getNeedASubPost,
  listMyNeedASubRequests,
  listNeedASubPostRequests,
} from './needASubApi.js'

export function useNeedASubDetailData({
  appUser,
  currentUser,
  postId,
}) {
  const [post, setPost] = useState(null)
  const [myRequests, setMyRequests] = useState([])
  const [ownerRequests, setOwnerRequests] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  const loadDetail = useCallback(async () => {
    setIsLoading(true)
    setError('')

    try {
      const postResponse = await getNeedASubPost(postId, currentUser)
      const isPostOwner = appUser?.id === postResponse.owner_user_id
      const [requestResponse, ownerRequestResponse] = await Promise.all([
        currentUser && !isPostOwner
          ? listMyNeedASubRequests(currentUser).catch(() => [])
          : Promise.resolve([]),
        currentUser && isPostOwner
          ? listNeedASubPostRequests(currentUser, postId).catch(() => [])
          : Promise.resolve([]),
      ])
      setPost(postResponse)
      setMyRequests(requestResponse)
      setOwnerRequests(ownerRequestResponse)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load post.')
    } finally {
      setIsLoading(false)
    }
  }, [appUser?.id, currentUser, postId])

  useEffect(() => {
    loadDetail()
  }, [loadDetail])

  return {
    error,
    isLoading,
    loadDetail,
    myRequests,
    ownerRequests,
    post,
    setError,
  }
}
