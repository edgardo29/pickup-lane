import { hasCompleteProfile } from './gameUserSelectors.js'
import { cancelGame } from './gameDetailsApi.js'

export function useGameDetailsLifecycleActions({
  canCancelGame,
  clearChatState,
  currentParticipant,
  currentUser,
  firebaseUser,
  game,
  isAuthLoading,
  isGameClosed,
  isHost,
  navigate,
  refreshParticipants,
  setIsCancelGameModalOpen,
  setIsCancellingGame,
  setJoinNotice,
  setShareCopied,
}) {
  async function handleCancelGame() {
    if (!game || !canCancelGame || !firebaseUser) {
      return
    }

    setIsCancellingGame(true)
    setJoinNotice('')

    try {
      await cancelGame(game.id, firebaseUser)
      await refreshParticipants()
      clearChatState()
      setIsCancelGameModalOpen(false)
      setJoinNotice('Game cancelled. Players were notified.')
    } catch (requestError) {
      setJoinNotice(
        requestError instanceof Error ? requestError.message : 'Unable to cancel this game.',
      )
    } finally {
      setIsCancellingGame(false)
    }
  }

  async function handleJoinIntent() {
    if (!game) {
      return
    }

    setShareCopied(false)

    if (isAuthLoading) {
      setJoinNotice('Checking your account...')
      return
    }

    if (!currentUser?.id) {
      navigate('/create-account', { state: { from: `/games/${game.id}` } })
      return
    }

    if (!hasCompleteProfile(currentUser)) {
      navigate('/finish-profile', { state: { from: `/games/${game.id}` } })
      return
    }

    if (isHost) {
      setJoinNotice('You are hosting this game.')
      return
    }

    if (currentParticipant) {
      setJoinNotice(
        currentParticipant.participant_status === 'waitlisted'
          ? 'You are already on the waitlist.'
          : 'You already joined this game.',
      )
      return
    }

    if (isGameClosed) {
      setJoinNotice('This game is not open for joining.')
      return
    }

    navigate(`/games/${game.id}/checkout`)
  }

  return {
    handleCancelGame,
    handleJoinIntent,
  }
}
