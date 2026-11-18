import { useEffect, useState } from 'react'
import { loadGameChangeReview, requestGameChangeRemoval } from './gameDetailsApi.js'

export function useGameChangeReview({ enabled, firebaseUser, gameId }) {
  const [review, setReview] = useState(null)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (!enabled) {
      return
    }

    let ignore = false
    async function loadReview() {
      setStatus('loading')
      setError('')
      try {
        const result = await loadGameChangeReview(gameId, firebaseUser)
        if (!ignore) {
          setReview(result)
          setStatus('success')
        }
      } catch (requestError) {
        if (!ignore) {
          setError(requestError instanceof Error ? requestError.message : 'Unable to review changes.')
          setStatus('error')
        }
      }
    }
    loadReview()

    return () => {
      ignore = true
    }
  }, [enabled, firebaseUser, gameId])

  async function submit(reliefChoice) {
    if (!enabled || isSubmitting) return false

    setIsSubmitting(true)
    setError('')
    try {
      const request = await requestGameChangeRemoval(gameId, firebaseUser, reliefChoice)
      setReview((current) => ({
        ...current,
        active_request: request,
        can_request_removal: false,
      }))
      setStatus('success')
      return true
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to request removal.')
      return false
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!enabled) return { error: '', isSubmitting: false, review: null, status: 'idle', submit }

  return { error, isSubmitting, review, status, submit }
}
