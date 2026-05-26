import { useCallback, useEffect, useState } from 'react'
import { hasCompleteProfile } from './gameUserSelectors.js'
import { loadGameCheckout } from './gameCheckoutApi.js'
import { listUserPaymentMethods } from '../../lib/paymentMethodsApi.js'

export function useGameCheckoutData({
  appUser,
  firebaseUser,
  gameId,
  isAuthLoading,
  navigate,
}) {
  const [game, setGame] = useState(null)
  const [venue, setVenue] = useState(null)
  const [images, setImages] = useState([])
  const [participants, setParticipants] = useState([])
  const [paymentMethods, setPaymentMethods] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')

  const reloadPaymentMethods = useCallback(async () => {
    if (!firebaseUser) {
      setPaymentMethods([])
      return []
    }

    const methods = await listUserPaymentMethods(firebaseUser)
    setPaymentMethods(methods)
    return methods
  }, [firebaseUser])

  useEffect(() => {
    let ignore = false

    async function loadCheckout() {
      if (isAuthLoading) {
        return
      }

      if (!appUser?.id) {
        navigate('/sign-in', { replace: true })
        return
      }

      if (!hasCompleteProfile(appUser)) {
        navigate('/finish-profile', { replace: true })
        return
      }

      setStatus('loading')
      setError('')

      try {
        const checkout = await loadGameCheckout({ firebaseUser, gameId })

        if (!ignore) {
          setGame(checkout.game)
          setVenue(checkout.venue)
          setImages(checkout.images)
          setParticipants(checkout.participants)
          setPaymentMethods(checkout.paymentMethods)
          setStatus('success')
        }
      } catch (requestError) {
        if (!ignore) {
          setError(requestError instanceof Error ? requestError.message : 'Unable to load checkout.')
          setStatus('error')
        }
      }
    }

    loadCheckout()

    return () => {
      ignore = true
    }
  }, [appUser, firebaseUser, gameId, isAuthLoading, navigate])

  return {
    error,
    game,
    images,
    participants,
    paymentMethods,
    reloadPaymentMethods,
    status,
    venue,
  }
}
