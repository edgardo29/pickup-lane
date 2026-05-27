import { useCallback, useRef, useState } from 'react'
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

export function useGameCheckoutActions({ navigate }) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [stripeCheckout, setStripeCheckout] = useState(null)
  const [stripeStatusMessage, setStripeStatusMessage] = useState('')
  const isSubmittingRef = useRef(false)

  const startSubmission = useCallback(function startSubmission() {
    if (isSubmittingRef.current) {
      return false
    }

    isSubmittingRef.current = true
    setIsSubmitting(true)
    return true
  }, [])

  const finishSubmission = useCallback(function finishSubmission() {
    isSubmittingRef.current = false
    setIsSubmitting(false)
  }, [])

  const resetSubmitError = useCallback(() => {
    setSubmitError('')
  }, [])

  const resetStripeCheckout = useCallback(() => {
    setStripeCheckout(null)
    setStripeStatusMessage('')
  }, [])

  const pollCheckoutStatus = useCallback(
    async ({ bookingId, firebaseUser, gameId }) => {
      let latestStatus = null

      for (let attempt = 0; attempt < CHECKOUT_STATUS_POLL_COUNT; attempt += 1) {
        latestStatus = await getGameCheckoutStatus({ bookingId, firebaseUser })

        if (
          latestStatus.booking_status === 'confirmed' &&
          latestStatus.booking_payment_status === 'paid' &&
          latestStatus.payment_status === 'succeeded'
        ) {
          navigate(`/games/${gameId}`, { replace: true })
          return latestStatus
        }

        if (
          ['failed', 'cancelled', 'expired'].includes(latestStatus.booking_status) ||
          ['failed', 'canceled'].includes(latestStatus.payment_status)
        ) {
          throw new Error('Payment could not be confirmed. Please try again.')
        }

        await wait(CHECKOUT_STATUS_POLL_DELAY_MS)
      }

      setStripeStatusMessage('Still confirming your spot.')
      return latestStatus
    },
    [navigate],
  )

  const prepareStripeCheckout = useCallback(
    async ({
      agreed,
      appUser,
      effectiveGuestCount,
      existingParticipant,
      firebaseUser,
      game,
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
        isJoinWindowClosed ||
        (existingParticipant && !isPaymentResume)
      ) {
        return null
      }

      if (!startSubmission()) {
        return null
      }

      setSubmitError('')
      setStripeStatusMessage('')

      try {
        const paymentIntent = await createGameCheckoutPaymentIntent({
          firebaseUser,
          gameId: game.id,
          guestCount: effectiveGuestCount,
          paymentMethodId,
          returnUrl,
        })

        if (!paymentIntent.payment_required) {
          navigate(`/games/${game.id}`, { replace: true })
          return paymentIntent
        }

        if (paymentMethodId) {
          if (paymentIntent.stripe_status === 'requires_action') {
            const stripe = await stripePromise
            if (!stripe) {
              throw new Error('Secure payment is not ready. Please try again.')
            }

            const nextActionResult = await stripe.handleNextAction({
              clientSecret: paymentIntent.client_secret,
            })
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
            bookingId: paymentIntent.booking_id,
            firebaseUser,
            gameId: game.id,
          })
          return paymentIntent
        }

        setStripeCheckout(paymentIntent)
        return paymentIntent
      } catch (requestError) {
        setSubmitError(
          requestError instanceof Error
            ? requestError.message
            : 'Unable to start secure checkout.',
        )
        return null
      } finally {
        finishSubmission()
      }
    },
    [finishSubmission, pollCheckoutStatus, startSubmission],
  )

  const confirmBooking = useCallback(
    async ({
      agreed,
      appUser,
      effectiveGuestCount,
      existingParticipant,
      game,
      isAddGuestsCheckout,
      isJoinWindowClosed,
    }) => {
      const isExistingConfirmedPlayer = existingParticipant?.participant_status === 'confirmed'
      if (
        !agreed ||
        !game ||
        !appUser?.id ||
        isJoinWindowClosed ||
        (!isAddGuestsCheckout && existingParticipant) ||
        (isAddGuestsCheckout && (!isExistingConfirmedPlayer || effectiveGuestCount <= 0))
      ) {
        return
      }

      if (!startSubmission()) {
        return
      }

      setSubmitError('')

      try {
        await confirmGameCheckout({
          gameId: game.id,
          guestCount: effectiveGuestCount,
          isAddGuestsCheckout,
          userId: appUser.id,
        })
        navigate(`/games/${game.id}`, { replace: true })
      } catch (requestError) {
        setSubmitError(requestError instanceof Error ? requestError.message : 'Unable to confirm booking.')
      } finally {
        finishSubmission()
      }
    },
    [finishSubmission, navigate, startSubmission],
  )

  return {
    confirmBooking,
    isSubmitting,
    prepareStripeCheckout,
    resetSubmitError,
    resetStripeCheckout,
    stripeCheckout,
    stripeStatusMessage,
    submitError,
  }
}
