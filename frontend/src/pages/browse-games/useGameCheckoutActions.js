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

export function describeCheckoutStatus(checkoutStatus) {
  if (
    checkoutStatus.booking_status === 'confirmed' &&
    checkoutStatus.booking_payment_status === 'paid' &&
    checkoutStatus.payment_status === 'succeeded'
  ) {
    return { outcome: 'confirmed', message: '' }
  }
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

        await wait(CHECKOUT_STATUS_POLL_DELAY_MS)
      }

      setStripeStatusMessage('Payment is still unresolved. Your spot will not remain held past expiry.')
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
    [finishSubmission, navigate, pollCheckoutStatus, startSubmission],
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

      if (!startSubmission()) {
        return
      }

      setSubmitError('')

      try {
        await confirmGameCheckout({
          gameId: game.id,
          guestCount: effectiveGuestCount,
          firebaseUser,
          isAddGuestsCheckout,
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
