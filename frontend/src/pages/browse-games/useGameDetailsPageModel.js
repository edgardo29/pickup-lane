import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth.js'
import { useAdminAccess } from '../admin/shared/useAdminAccess.js'
import { buildGameDetailsLayoutProps } from './gameDetailsLayoutProps.js'
import { useGameDetailsActions } from './useGameDetailsActions.js'
import { useGameDetailsChat } from './useGameDetailsChat.js'
import { useGameDetailsData } from './useGameDetailsData.js'
import { useGameDetailsDerivedState } from './useGameDetailsDerivedState.js'
import { useGameDetailsUiState } from './useGameDetailsUiState.js'

export function useGameDetailsPageModel() {
  const { gameId } = useParams()
  const navigate = useNavigate()
  const { appUser, currentUser: firebaseUser, isLoading: isAuthLoading } = useAuth()
  const shouldLoadAdminAccess = appUser?.role === 'admin'
  const { hasAdminAccess } = useAdminAccess({
    enabled: shouldLoadAdminAccess,
  })
  const uiState = useGameDetailsUiState()
  const {
    activeImageIndex,
    activePlayerTab,
    isAddingHostGuest,
    isCancelGameModalOpen,
    isCancellingGame,
    isHostGuestModalOpen,
    isJoining,
    isLeaveModalOpen,
    isLeaving,
    isPlayerListOpen,
    isUpdatingGuests,
    joinNotice,
    nowMs,
    resetUiState,
    setActiveImageIndex,
    setActivePlayerTab,
    setIsAddingHostGuest,
    setIsCancelGameModalOpen,
    setIsCancellingGame,
    setIsHostGuestModalOpen,
    setIsLeaveModalOpen,
    setIsLeaving,
    setIsPlayerListOpen,
    setIsUpdatingGuests,
    setJoinNotice,
    setShareCopied,
    shareCopied,
  } = uiState
  const detailsData = useGameDetailsData({
    appUser,
    firebaseUser,
    gameId,
    onBeforeLoad: () => {
      resetUiState()
      resetChatState()
    },
  })
  const {
    communityGameDetails,
    currentUser,
    error,
    game,
    gameImages,
    loadedChatState,
    participants,
    refreshParticipants,
    status,
    venue,
  } = detailsData
  const derivedState = useGameDetailsDerivedState({
    canAdminCancelCommunityGame: hasAdminAccess,
    canAdminCancelOfficialGame: hasAdminAccess,
    communityGameDetails,
    currentUser,
    game,
    gameImages,
    isJoining,
    nowMs,
    participants,
    venue,
  })
  const {
    chatSenderNames,
    currentGuestCount,
    currentParticipant,
    images,
    participantSummary,
    viewModel,
  } = derivedState
  const chat = useGameDetailsChat({
    canOpenGameChat: viewModel?.canOpenGameChat || false,
    firebaseUser,
    gameId: game?.id || gameId,
    onJoinNotice: setJoinNotice,
    onShareCopiedChange: setShareCopied,
  })
  const {
    chatDraft,
    chatError,
    chatMessages,
    clearChatState,
    closeChat,
    handleOpenChat,
    handleSendChatMessage,
    hasUnreadChat,
    hydrateChatState,
    isChatOpen,
    isSendingChatMessage,
    resetChatState,
    setChatDraft,
  } = chat

  useEffect(() => {
    hydrateChatState(loadedChatState)
  }, [hydrateChatState, loadedChatState])

  const actions = useGameDetailsActions({
    canAddBookingGuests: viewModel?.canAddBookingGuests || false,
    canCancelGame: viewModel?.canCancelGame || false,
    clearChatState,
    currentGuestCount,
    currentParticipant,
    currentUser,
    firebaseUser,
    game,
    images,
    isAuthLoading,
    isGameClosed: viewModel?.isGameClosed || false,
    isHost: Boolean(viewModel?.isHost),
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
    title: viewModel?.title || '',
    venueName: viewModel?.venueName || '',
  })

  return {
    error,
    game,
    layoutProps: buildGameDetailsLayoutProps({
      actions,
      activeImageIndex,
      activePlayerTab,
      chatDraft,
      chatError,
      chatMessages,
      chatSenderNames,
      closeChat,
      currentGuestCount,
      currentParticipant,
      currentUser,
      game,
      handleOpenChat,
      handleSendChatMessage,
      hasUnreadChat,
      images,
      isAddingHostGuest,
      isCancelGameModalOpen,
      isCancellingGame,
      isChatOpen,
      isHostGuestModalOpen,
      isLeaveModalOpen,
      isLeaving,
      isPlayerListOpen,
      isSendingChatMessage,
      isUpdatingGuests,
      joinNotice,
      latestChatMessage: chatMessages.at(-1) || null,
      navigate,
      participantSummary,
      setActiveImageIndex,
      setActivePlayerTab,
      setChatDraft,
      setIsCancelGameModalOpen,
      setIsHostGuestModalOpen,
      setIsLeaveModalOpen,
      setIsPlayerListOpen,
      shareCopied,
      viewModel,
    }),
    status,
    viewModel,
  }
}
