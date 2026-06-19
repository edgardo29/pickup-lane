import { useMemo } from 'react'
import defaultCommunityVenueImage from '../../assets/community-default/default-venue-wide.png'
import { buildMediaUrl } from '../../lib/apiClient.js'
import {
  ACTIVE_JOIN_STATUSES,
  buildChatSenderNames,
  getCurrentGuestCount,
  getParticipantSummary,
} from './gameParticipantSelectors.js'
import { buildGameDetailsViewModel } from './gameDetailsViewModel.jsx'

export function useGameDetailsDerivedState({
  canAdminCancelCommunityGame = false,
  canAdminCancelOfficialGame = false,
  communityGameDetails,
  currentUser,
  game,
  gameImages,
  isJoining,
  nowMs,
  participants,
  venue,
}) {
  const images = useMemo(
    () => {
      const galleryImages = gameImages
        .slice()
        .sort(
          (first, second) =>
            Number(second.is_primary) - Number(first.is_primary) ||
            first.sort_order - second.sort_order ||
            new Date(first.created_at) - new Date(second.created_at),
        )
        .map((image) => buildMediaUrl(image.image_url))

      if (galleryImages.length === 0 && game?.game_type === 'community') {
        return [defaultCommunityVenueImage]
      }

      return galleryImages
    },
    [game?.game_type, gameImages],
  )

  const participantSummary = useMemo(
    () => getParticipantSummary(participants, game?.total_spots),
    [game?.total_spots, participants],
  )
  const currentParticipant = useMemo(
    () =>
      participants.find(
        (participant) =>
          participant.user_id === currentUser?.id &&
          ACTIVE_JOIN_STATUSES.has(participant.participant_status),
      ) || null,
    [currentUser?.id, participants],
  )
  const currentGuestCount = useMemo(
    () => getCurrentGuestCount(participants, currentParticipant, currentUser?.id),
    [currentParticipant, currentUser?.id, participants],
  )
  const viewModel = useMemo(
    () => {
      if (!game) {
        return null
      }

      return buildGameDetailsViewModel({
        canAdminCancelCommunityGame,
        canAdminCancelOfficialGame,
        communityGameDetails,
        currentGuestCount,
        currentParticipant,
        currentUser,
        game,
        isJoining,
        nowMs,
        participantSummary,
        participants,
        venue,
      })
    },
    [
      canAdminCancelCommunityGame,
      canAdminCancelOfficialGame,
      communityGameDetails,
      currentGuestCount,
      currentParticipant,
      currentUser,
      game,
      isJoining,
      nowMs,
      participantSummary,
      participants,
      venue,
    ],
  )
  const chatSenderNames = useMemo(() => buildChatSenderNames(participants), [participants])

  return {
    chatSenderNames,
    currentGuestCount,
    currentParticipant,
    images,
    participantSummary,
    viewModel,
  }
}
