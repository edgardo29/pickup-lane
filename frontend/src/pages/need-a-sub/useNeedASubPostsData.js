import { useCallback, useEffect, useState } from 'react'
import {
  listMyNeedASubPosts,
  listNeedASubPosts,
} from './needASubApi.js'

export function useNeedASubPostsData({
  currentUser,
  isAuthLoading,
}) {
  const [posts, setPosts] = useState([])
  const [myPosts, setMyPosts] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  const refreshNeedASub = useCallback(async ({ showLoading = false } = {}) => {
    if (showLoading) {
      setIsLoading(true)
    }
    setError('')

    try {
      const [postsResponse, myPostsResponse] = await Promise.all([
        listNeedASubPosts(),
        currentUser ? listMyNeedASubPosts(currentUser).catch(() => []) : Promise.resolve([]),
      ])

      setPosts(postsResponse)
      setMyPosts(myPostsResponse)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load Need a Sub.')
    } finally {
      if (showLoading) {
        setIsLoading(false)
      }
    }
  }, [currentUser])

  useEffect(() => {
    let ignore = false

    async function loadInitialNeedASub() {
      if (isAuthLoading) {
        return
      }

      setIsLoading(true)
      setError('')

      try {
        const [postsResponse, myPostsResponse] = await Promise.all([
          listNeedASubPosts(),
          currentUser ? listMyNeedASubPosts(currentUser).catch(() => []) : Promise.resolve([]),
        ])

        if (!ignore) {
          setPosts(postsResponse)
          setMyPosts(myPostsResponse)
        }
      } catch (loadError) {
        if (!ignore) {
          setError(loadError instanceof Error ? loadError.message : 'Unable to load Need a Sub.')
        }
      } finally {
        if (!ignore) {
          setIsLoading(false)
        }
      }
    }

    loadInitialNeedASub()

    return () => {
      ignore = true
    }
  }, [currentUser, isAuthLoading])

  useEffect(() => {
    function refreshVisibleNeedASub() {
      if (document.visibilityState === 'visible') {
        refreshNeedASub()
      }
    }

    window.addEventListener('focus', refreshNeedASub)
    document.addEventListener('visibilitychange', refreshVisibleNeedASub)

    return () => {
      window.removeEventListener('focus', refreshNeedASub)
      document.removeEventListener('visibilitychange', refreshVisibleNeedASub)
    }
  }, [refreshNeedASub])

  return {
    error,
    isLoading,
    myPosts,
    posts,
    refreshNeedASub,
    setError,
  }
}
