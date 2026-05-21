import { useGameDetailsAttendanceActions } from './useGameDetailsAttendanceActions.js'
import { useGameDetailsLifecycleActions } from './useGameDetailsLifecycleActions.js'
import { useGameDetailsShareAction } from './useGameDetailsShareAction.js'

export function useGameDetailsActions({
  canAddBookingGuests,
  canCancelGame,
  clearChatState,
  currentGuestCount,
  currentParticipant,
  currentUser,
  firebaseUser,
  game,
  images,
  isAuthLoading,
  isGameClosed,
  isHost,
  navigate,
  refreshParticipants,
  setActiveImageIndex,
  setIsAddingHostGuest,
  setIsCancelGameModalOpen,
  setIsCancellingGame,
  setIsHostGuestModalOpen,
  setIsLeaveModalOpen,
  setIsLeaving,
  setIsUpdatingGuests,
  setJoinNotice,
  setShareCopied,
  title,
  venueName,
}) {
  function handlePreviousImage() {
    setActiveImageIndex((currentIndex) =>
      currentIndex === 0 ? images.length - 1 : currentIndex - 1,
    )
  }

  function handleNextImage() {
    setActiveImageIndex((currentIndex) =>
      currentIndex === images.length - 1 ? 0 : currentIndex + 1,
    )
  }

  const { handleShareGame } = useGameDetailsShareAction({
    game,
    setShareCopied,
    title,
    venueName,
  })
  const {
    handleCancelGame,
    handleJoinIntent,
  } = useGameDetailsLifecycleActions({
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
  })
  const {
    handleAddBookingGuests,
    handleLeaveGame,
    handleRemoveGuests,
    handleSaveHostGuestCount,
  } = useGameDetailsAttendanceActions({
    canAddBookingGuests,
    currentGuestCount,
    currentParticipant,
    currentUser,
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
  })

  return {
    handleAddBookingGuests,
    handleCancelGame,
    handleJoinIntent,
    handleLeaveGame,
    handleNextImage,
    handlePreviousImage,
    handleRemoveGuests,
    handleSaveHostGuestCount,
    handleShareGame,
  }
}
