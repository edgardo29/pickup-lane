import { useEffect, useRef, useState } from 'react'
import {
  loadGameDetails as loadGameDetailsData,
  refreshGameParticipants as refreshGameParticipantsData,
} from './gameDetailsApi.js'

const EMPTY_CHAT_STATE = {
  activeChat: null,
  chatMessages: [],
  hasUnreadChat: false,
}

export function useGameDetailsData({
  appUser,
  firebaseUser,
  gameId,
  onBeforeLoad,
}) {
  const [game, setGame] = useState(null)
  const [venue, setVenue] = useState(null)
  const [gameImages, setGameImages] = useState([])
  const [communityGameDetails, setCommunityGameDetails] = useState(null)
  const [participants, setParticipants] = useState([])
  const [currentUser, setCurrentUser] = useState(null)
  const [loadedChatState, setLoadedChatState] = useState(EMPTY_CHAT_STATE)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const onBeforeLoadRef = useRef(onBeforeLoad)

  useEffect(() => {
    onBeforeLoadRef.current = onBeforeLoad
  }, [onBeforeLoad])

  useEffect(() => {
    let ignore = false

    async function loadGameDetails() {
      setStatus('loading')
      setError('')
      setLoadedChatState(EMPTY_CHAT_STATE)
      onBeforeLoadRef.current()

      try {
        const details = await loadGameDetailsData({ appUser, firebaseUser, gameId })

        if (!ignore) {
          setGame(details.game)
          setVenue(details.venue)
          setGameImages(details.gameImages)
          setCommunityGameDetails(details.communityGameDetails)
          setParticipants(details.participants)
          setCurrentUser(appUser || null)
          setLoadedChatState({
            activeChat: details.activeChat,
            chatMessages: details.chatMessages,
            hasUnreadChat: details.hasUnreadChat,
          })
          setStatus('success')
        }
      } catch (requestError) {
        if (!ignore) {
          setError(requestError instanceof Error ? requestError.message : 'Unable to load game.')
          setStatus('error')
        }
      }
    }

    loadGameDetails()

    return () => {
      ignore = true
    }
  }, [appUser, firebaseUser, gameId])

  async function refreshParticipants() {
    const gameDetails = await refreshGameParticipantsData(gameId)
    setParticipants(gameDetails.participants)
    setGame(gameDetails.game)
  }

  return {
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
  }
}
