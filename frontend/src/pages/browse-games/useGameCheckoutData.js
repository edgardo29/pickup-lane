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
  const [paymentMethodsError, setPaymentMethodsError] = useState('')
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')

  const reconcileCheckoutStatus = useCallback((checkoutStatus) => {
    if (checkoutStatus.roster_counts) {
      setGame((current) => current ? { ...current, roster_counts: checkoutStatus.roster_counts } : current)
    }
    const guestAttemptEnded = ['confirmed', 'partially_cancelled'].includes(checkoutStatus.booking_status) && (
      ['requires_payment_method', 'failed', 'canceled'].includes(checkoutStatus.payment_status) ||
      Boolean(checkoutStatus.compensation_status) ||
      checkoutStatus.guest_reservation_status === 'released'
    )
    if (checkoutStatus.reservation_status !== 'released' && !guestAttemptEnded) {
      return
    }

    // Drop the released party from the loaded roster so it cannot become a
    // pending booking again when the player starts a new payment attempt.
    setParticipants((current) => current.filter((participant) => !(
      participant.booking_id === checkoutStatus.booking_id &&
      participant.participant_status === 'pending_payment' &&
      (checkoutStatus.reservation_status === 'released' || participant.participant_type === 'guest')
    )))
  }, [])

  const reloadPaymentMethods = useCallback(async () => {
    if (!firebaseUser) {
      setPaymentMethods([])
      return []
    }

    try {
      const methods = await listUserPaymentMethods(firebaseUser)
      setPaymentMethods(methods)
      setPaymentMethodsError('')
      return methods
    } catch (requestError) {
      setPaymentMethodsError('Saved cards could not be loaded. Try again.')
      throw requestError
    }
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
          setPaymentMethodsError(checkout.paymentMethodsError)
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
    paymentMethodsError,
    reloadPaymentMethods,
    reconcileCheckoutStatus,
    status,
    venue,
  }
}
