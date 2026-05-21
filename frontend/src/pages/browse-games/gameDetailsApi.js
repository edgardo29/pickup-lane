import { apiRequest } from '../../lib/apiClient.js'
import { canUseGameChat } from './gameDetailsSelectors.js'
import { buildChatMessagesPath, getChatAuthHeaders } from './gameDetailsChat.js'

export async function loadGameDetails({ appUser, firebaseUser, gameId }) {
  const game = await apiRequest(`/games/${gameId}`)

  const [gameImages, participants, venue] = await Promise.all([
    apiRequest(`/game-images?game_id=${gameId}&image_status=active`),
    apiRequest(`/game-participants?game_id=${gameId}`),
    apiRequest(`/venues/${game.venue_id}`).catch(() => null),
  ])
  const communityGameDetails = game.game_type === 'community'
    ? await apiRequest(`/community-game-details?game_id=${gameId}`)
      .then((details) => details[0] || null)
      .catch(() => null)
    : null
  const canLoadChat = canUseGameChat(game, participants, appUser)
  let activeChat = null
  let chatMessages = []

  if (game.is_chat_enabled && canLoadChat && firebaseUser) {
    activeChat = await getOrCreateGameChat(gameId, firebaseUser).catch(() => null)

    if (activeChat) {
      chatMessages = await loadVisibleChatMessages(activeChat.id, firebaseUser).catch(() => [])
    }
  }

  return {
    activeChat,
    chatMessages,
    communityGameDetails,
    game,
    gameImages,
    hasUnreadChat: Boolean(activeChat?.unread_count),
    participants,
    venue,
  }
}

export async function refreshGameParticipants(gameId) {
  const [participants, game] = await Promise.all([
    apiRequest(`/game-participants?game_id=${gameId}`),
    apiRequest(`/games/${gameId}`),
  ])

  return { game, participants }
}

export async function cancelGame(gameId, firebaseUser) {
  return apiRequest(`/games/${gameId}/cancel`, {
    method: 'POST',
    headers: {
      ...(await getChatAuthHeaders(firebaseUser)),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({}),
  })
}

export async function leaveGame(gameId, userId) {
  return apiRequest(`/games/${gameId}/leave`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ acting_user_id: userId }),
  })
}

export async function addHostGuests(gameId, userId, guestCount) {
  return apiRequest(`/games/${gameId}/guests/add`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ acting_user_id: userId, guest_count: guestCount }),
  })
}

export async function removeGameGuests(gameId, userId, removeCount) {
  return apiRequest(`/games/${gameId}/guests/remove`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ acting_user_id: userId, remove_count: removeCount }),
  })
}

export async function openGameChat({ activeChat, firebaseUser, gameId }) {
  const chat = activeChat?.id
    ? activeChat
    : await getOrCreateGameChat(gameId, firebaseUser)
  const messages = await loadVisibleChatMessages(chat.id, firebaseUser).catch(() => [])

  await markGameChatRead(chat.id, firebaseUser)

  return { chat, messages }
}

export async function getGameChatReadState(chatId, firebaseUser) {
  return apiRequest(`/game-chats/${chatId}/read-state`, {
    headers: await getChatAuthHeaders(firebaseUser),
  })
}

export async function loadVisibleChatMessages(chatId, firebaseUser, afterCreatedAt = '') {
  return apiRequest(
    buildChatMessagesPath(chatId, afterCreatedAt),
    { headers: await getChatAuthHeaders(firebaseUser) },
  )
}

export async function markGameChatRead(chatId, firebaseUser) {
  return apiRequest(`/game-chats/${chatId}/read`, {
    method: 'POST',
    headers: {
      ...(await getChatAuthHeaders(firebaseUser)),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({}),
  })
}

export async function sendGameChatMessage(chatId, firebaseUser, messageBody) {
  return apiRequest('/chat-messages', {
    method: 'POST',
    headers: {
      ...(await getChatAuthHeaders(firebaseUser)),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      chat_id: chatId,
      message_body: messageBody,
    }),
  })
}

async function getOrCreateGameChat(gameId, firebaseUser) {
  return apiRequest(`/game-chats/for-game/${gameId}`, {
    method: 'POST',
    headers: {
      ...(await getChatAuthHeaders(firebaseUser)),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({}),
  })
}
