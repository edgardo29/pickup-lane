import {
  addHostGuests,
  leaveGame,
  removeGameGuests,
} from './gameDetailsApi.js'

export function useGameDetailsAttendanceActions({
  canAddBookingGuests,
  currentGuestCount,
  currentParticipant,
  currentUser,
  firebaseUser,
  game,
  isHost,
  navigate,
  refreshParticipants,
  setIsAddingHostGuest,
  setIsHostGuestModalOpen,
  setIsLeaveModalOpen,
  setIsLeaving,
  setIsUpdatingGuests,
  setJoinNotice,
  setShareCopied,
}) {
  async function handleLeaveGame() {
    if (!game || !currentUser?.id || !firebaseUser || !currentParticipant) {
      setIsLeaveModalOpen(false)
      return
    }

    setIsLeaving(true)
    setJoinNotice('')

    try {
      await leaveGame(game.id, firebaseUser)
      await refreshParticipants()
      setJoinNotice('')
      setIsLeaveModalOpen(false)
    } catch (requestError) {
      setJoinNotice(
        requestError instanceof Error ? requestError.message : 'Unable to leave this game.',
      )
    } finally {
      setIsLeaving(false)
    }
  }

  async function handleSaveHostGuestCount(nextGuestCount) {
    if (!game || !currentUser?.id || !firebaseUser || !isHost) {
      return
    }

    const guestDelta = nextGuestCount - currentGuestCount
    if (guestDelta === 0) {
      setIsHostGuestModalOpen(false)
      return
    }

    setJoinNotice('')

    if (guestDelta > 0) {
      setIsAddingHostGuest(true)

      try {
        await addHostGuests(game.id, firebaseUser, guestDelta)
        await refreshParticipants()
        setIsHostGuestModalOpen(false)
      } catch (requestError) {
        setJoinNotice(
          requestError instanceof Error ? requestError.message : 'Unable to update host guests.',
        )
      } finally {
        setIsAddingHostGuest(false)
      }

      return
    }

    await handleRemoveGuests(Math.abs(guestDelta), { closeHostGuestModal: true })
  }

  function handleAddBookingGuests(guestCount) {
    if (!game || !currentUser?.id || !canAddBookingGuests || guestCount <= 0) {
      return
    }

    setJoinNotice('')
    setShareCopied(false)
    navigate(`/games/${game.id}/checkout?mode=add-guests&guest_count=${guestCount}`)
  }

  async function handleRemoveGuests(removeCount, options = {}) {
    if (
      !game ||
      !currentUser?.id ||
      !firebaseUser ||
      !currentParticipant ||
      removeCount <= 0
    ) {
      return
    }

    setIsUpdatingGuests(true)
    setJoinNotice('')

    try {
      await removeGameGuests(game.id, firebaseUser, removeCount)
      await refreshParticipants()
      setIsLeaveModalOpen(false)
      if (options.closeHostGuestModal) {
        setIsHostGuestModalOpen(false)
      }
    } catch (requestError) {
      setJoinNotice(
        requestError instanceof Error ? requestError.message : 'Unable to update attendance.',
      )
    } finally {
      setIsUpdatingGuests(false)
    }
  }

  return {
    handleAddBookingGuests,
    handleLeaveGame,
    handleRemoveGuests,
    handleSaveHostGuestCount,
  }
}
