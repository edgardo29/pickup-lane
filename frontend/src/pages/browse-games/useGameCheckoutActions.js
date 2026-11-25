import { useCallback, useEffect, useRef, useState } from 'react'
import {
  confirmGameCheckout,
  createGameCheckoutPaymentIntent,
  getGameCheckoutStatus,
} from './gameCheckoutApi.js'

const CHECKOUT_STATUS_POLL_COUNT = 12
const CHECKOUT_STATUS_POLL_DELAY_MS = 1200

function wait(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds))
}

export function describeCheckoutStatus(checkoutStatus) {
  if (checkoutStatus.booking_status === 'capacity_conflict') {
    return {
      outcome: 'stopped',
      message: 'Your payment completed, but the spot could not be confirmed. A refund is required.',
    }
  }
  if (
    checkoutStatus.booking_status === 'expired' &&
    checkoutStatus.payment_status === 'succeeded'
  ) {
    return {
      outcome: 'stopped',
      message: 'Your payment completed after the spot expired. A refund is required.',
    }
  }
  // Added guests whose payment arrived too late: the booking itself stays
  // confirmed, but that payment is being refunded.
  if (checkoutStatus.compensation_status) {
    return {
      outcome: 'stopped',
      message: 'Your payment completed, but the guests could not be added. A refund is required.',
    }
  }
  if (checkoutStatus.guest_reservation_status === 'released' &&
    !['requires_payment_method', 'failed', 'canceled'].includes(checkoutStatus.payment_status)) {
    return {
      outcome: 'stopped',
      message: checkoutStatus.payment_status === 'succeeded'
        ? 'Your payment completed, but the guests could not be added. A refund is required.'
        : 'The guest hold ended without adding the guests. Payment is still unresolved; a late successful charge requires a refund.',
    }
  }
  if (
    ['confirmed', 'partially_cancelled'].includes(checkoutStatus.booking_status) &&
    checkoutStatus.payment_status === 'succeeded'
  ) {
    return { outcome: 'confirmed', message: '' }
  }
  if (checkoutStatus.booking_status === 'expired') {
    return {
      outcome: 'stopped',
      message: 'The spot expired while payment was unresolved. Payment status is still being checked.',
    }
  }
  if (checkoutStatus.payment_status === 'requires_payment_method') {
    return { outcome: 'retry_card', message: 'Choose another saved card to continue.' }
  }
  if (checkoutStatus.payment_status === 'requires_action') {
    return { outcome: 'pending', message: 'Payment authentication is required.' }
  }
  if (checkoutStatus.payment_status === 'requires_confirmation') {
    return { outcome: 'pending', message: 'Payment is ready for secure confirmation.' }
  }
  if (checkoutStatus.payment_status === 'requires_capture') {
    return {
      outcome: 'pending',
      message: 'Payment is unresolved and no spot has been confirmed.',
    }
  }
  if (checkoutStatus.payment_status === 'unknown') {
    return {
      outcome: 'pending',
      message: 'The payment result is not available yet. Your spot will not remain held past expiry.',
    }
  }
  if (
    ['failed', 'cancelled'].includes(checkoutStatus.booking_status) ||
    ['failed', 'canceled'].includes(checkoutStatus.payment_status)
  ) {
    return { outcome: 'failed', message: 'Payment could not be confirmed. Please try again.' }
  }
  return { outcome: 'pending', message: 'Confirming payment and your spot...' }
}

export function useGameCheckoutActions({ navigate, onCheckoutStatus }) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [checkoutPayment, setCheckoutPayment] = useState(null)
  const [submittedGuestCount, setSubmittedGuestCount] = useState(null)
  const [stripeStatusMessage, setStripeStatusMessage] = useState('')
  const isSubmittingRef = useRef(false)
  const currentOwnerRef = useRef(null)

  const updateCheckoutPayment = useCallback((checkoutStatus) => {
    setCheckoutPayment(checkoutStatus)
    onCheckoutStatus(checkoutStatus)
  }, [onCheckoutStatus])

  const startSubmission = useCallback(function startSubmission() {
    if (isSubmittingRef.current || !currentOwnerRef.current) {
      return false
    }

    isSubmittingRef.current = true
    setIsSubmitting(true)
    return currentOwnerRef.current
  }, [])

  const finishSubmission = useCallback(function finishSubmission() {
    isSubmittingRef.current = false
    setIsSubmitting(false)
  }, [])

  // The page keys this checkout by account, game, and mode. Leaving that
  // checkout invalidates its outstanding requests without changing saved work.
  useEffect(() => {
    currentOwnerRef.current = {}
    return () => { currentOwnerRef.current = null }
  }, [])

  const isCurrentSubmission = useCallback((owner) => currentOwnerRef.current === owner, [])

  const pollCheckoutStatus = useCallback(
    async ({ bookingId, firebaseUser, gameId, owner, stripePromise = null }) => {
      let latestStatus = null
      const authenticatedPayments = new Set()

      for (let attempt = 0; attempt < CHECKOUT_STATUS_POLL_COUNT; attempt += 1) {
        if (!isCurrentSubmission(owner)) return null
        latestStatus = await getGameCheckoutStatus({ bookingId, firebaseUser })
        if (!isCurrentSubmission(owner)) return null
        updateCheckoutPayment(latestStatus)
        const presentation = describeCheckoutStatus(latestStatus)
        if (presentation.outcome === 'confirmed') {
          navigate(`/games/${gameId}`, { replace: true })
          return latestStatus
        }
        if (['failed', 'retry_card'].includes(presentation.outcome)) {
          throw new Error(presentation.message)
        }
        if (presentation.outcome === 'stopped') {
          setStripeStatusMessage(presentation.message)
          return latestStatus
        }

        setStripeStatusMessage(presentation.message)

        if (
          stripePromise && latestStatus.payment_status === 'requires_action' &&
          latestStatus.guest_reservation_status === 'held' && latestStatus.client_secret &&
          !authenticatedPayments.has(latestStatus.payment_id)
        ) {
          const stripe = await stripePromise
          if (!isCurrentSubmission(owner)) return null
          if (!stripe) throw new Error('Secure payment is not ready. Please try again.')
          authenticatedPayments.add(latestStatus.payment_id)
          const result = await stripe.handleNextAction({ clientSecret: latestStatus.client_secret })
          if (!isCurrentSubmission(owner)) return null
          if (result.error) {
            throw new Error(result.error.message || 'Payment authentication failed.')
          }
          // Authentication alone is not confirmation; read the existing
          // payment again before returning to Game Details.
          continue
        }

        await wait(CHECKOUT_STATUS_POLL_DELAY_MS)
      }

      if (!isCurrentSubmission(owner)) return null
      setStripeStatusMessage('Payment is still unresolved. Your spot will not remain held past expiry.')
      return latestStatus
    },
    [isCurrentSubmission, navigate, updateCheckoutPayment],
  )

  const prepareStripeCheckout = useCallback(
    async ({
      agreed,
      appUser,
      effectiveGuestCount,
      existingParticipant,
      firebaseUser,
      game,
      isAddGuestsCheckout = false,
      isJoinWindowClosed,
      isPaymentResume,
      paymentMethodId,
      returnUrl,
      stripePromise,
    }) => {
      if (
        !agreed ||
        !game ||
        !appUser?.id ||
        !firebaseUser ||
        (isJoinWindowClosed && !(isAddGuestsCheckout && isPaymentResume)) ||
        (!isAddGuestsCheckout && existingParticipant && !isPaymentResume) ||
        (isAddGuestsCheckout &&
          (existingParticipant?.participant_status !== 'confirmed' || effectiveGuestCount <= 0))
      ) {
        return null
      }

      const owner = startSubmission()
      if (!owner) {
        return null
      }

      setSubmitError('')
      setStripeStatusMessage('')

      try {
        if (isAddGuestsCheckout && isPaymentResume) {
          setStripeStatusMessage('Checking your guest payment...')
          return await pollCheckoutStatus({
            owner,
            stripePromise,
            bookingId: existingParticipant.booking_id,
            firebaseUser,
            gameId: game.id,
          })
        }

        const paymentIntent = await createGameCheckoutPaymentIntent({
          addGuests: isAddGuestsCheckout,
          firebaseUser,
          gameId: game.id,
          guestCount: effectiveGuestCount,
          paymentMethodId,
          returnUrl,
        })

        if (!isCurrentSubmission(owner)) return null
        setSubmittedGuestCount(effectiveGuestCount)
        updateCheckoutPayment(paymentIntent)

        if (!paymentIntent.payment_required) {
          navigate(`/games/${game.id}`, { replace: true })
          return paymentIntent
        }

        if (paymentMethodId) {
          if (paymentIntent.stripe_status === 'requires_action') {
            const stripe = await stripePromise
            if (!isCurrentSubmission(owner)) return null
            if (!stripe) {
              throw new Error('Secure payment is not ready. Please try again.')
            }

            const nextActionResult = await stripe.handleNextAction({
              clientSecret: paymentIntent.client_secret,
            })
            if (!isCurrentSubmission(owner)) return null
            if (nextActionResult.error) {
              throw new Error(
                nextActionResult.error.message || 'Payment authentication failed.',
              )
            }
          }

          if (paymentIntent.stripe_status === 'requires_payment_method') {
            throw new Error('This saved card could not be charged. Choose another card.')
          }

          setStripeStatusMessage('Confirming your spot...')
          await pollCheckoutStatus({
            owner,
            bookingId: paymentIntent.booking_id,
            firebaseUser,
            gameId: game.id,
          })
          return paymentIntent
        }

        return paymentIntent
      } catch (requestError) {
        if (!isCurrentSubmission(owner)) return null
        setSubmitError(
          requestError instanceof Error
            ? requestError.message
            : 'Unable to start secure checkout.',
        )
        return null
      } finally {
        if (isCurrentSubmission(owner)) finishSubmission()
      }
    },
    [finishSubmission, isCurrentSubmission, navigate, pollCheckoutStatus, startSubmission, updateCheckoutPayment],
  )

  const confirmBooking = useCallback(
    async ({
      agreed,
      appUser,
      effectiveGuestCount,
      existingParticipant,
      firebaseUser,
      game,
      isAddGuestsCheckout,
      isJoinWindowClosed,
      waitlistPaymentMethodId,
    }) => {
      const isExistingConfirmedPlayer = existingParticipant?.participant_status === 'confirmed'
      if (
        !agreed ||
        !game ||
        !appUser?.id ||
        !firebaseUser ||
        isJoinWindowClosed ||
        (!isAddGuestsCheckout && existingParticipant) ||
        (isAddGuestsCheckout && (!isExistingConfirmedPlayer || effectiveGuestCount <= 0))
      ) {
        return
      }

      const owner = startSubmission()
      if (!owner) {
        return
      }

      setSubmitError('')

      try {
        await confirmGameCheckout({
          gameId: game.id,
          guestCount: effectiveGuestCount,
          firebaseUser,
          isAddGuestsCheckout,
          waitlistPaymentMethodId,
        })
        if (!isCurrentSubmission(owner)) return
        navigate(`/games/${game.id}`, { replace: true })
      } catch (requestError) {
        if (!isCurrentSubmission(owner)) return null
        setSubmitError(requestError instanceof Error ? requestError.message : 'Unable to confirm booking.')
      } finally {
        if (isCurrentSubmission(owner)) finishSubmission()
      }
    },
    [finishSubmission, isCurrentSubmission, navigate, startSubmission],
  )

  return {
    confirmBooking,
    isSubmitting,
    prepareStripeCheckout,
    checkoutPayment,
    submittedGuestCount,
    stripeStatusMessage,
    submitError,
  }
}
