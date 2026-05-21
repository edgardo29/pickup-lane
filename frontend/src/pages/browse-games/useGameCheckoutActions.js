import { useCallback, useState } from 'react'
import { confirmGameCheckout } from './gameCheckoutApi.js'

export function useGameCheckoutActions({ navigate }) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')

  const resetSubmitError = useCallback(() => {
    setSubmitError('')
  }, [])

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

      setIsSubmitting(true)
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
        setIsSubmitting(false)
      }
    },
    [navigate],
  )

  return {
    confirmBooking,
    isSubmitting,
    resetSubmitError,
    submitError,
  }
}
