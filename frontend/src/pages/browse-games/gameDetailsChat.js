export async function getChatAuthHeaders(firebaseUser) {
  const token = await firebaseUser.getIdToken()
  return {
    Authorization: `Bearer ${token}`,
  }
}

export function buildChatMessagesPath(chatId, afterCreatedAt = '') {
  const query = new URLSearchParams({
    chat_id: chatId,
    moderation_status: 'visible',
    limit: '50',
  })

  if (afterCreatedAt) {
    query.set('after_created_at', afterCreatedAt)
  }

  return `/chat-messages?${query.toString()}`
}

export function getLatestMessageCreatedAt(messages) {
  if (!messages.length) {
    return ''
  }

  return messages.reduce((latest, message) => (
    !latest || new Date(message.created_at) > new Date(latest) ? message.created_at : latest
  ), '')
}

export function mergeChatMessages(currentMessages, incomingMessages) {
  const messagesById = new Map()

  for (const message of [...currentMessages, ...incomingMessages]) {
    messagesById.set(message.id, message)
  }

  return [...messagesById.values()]
    .sort((first, second) => new Date(first.created_at) - new Date(second.created_at))
    .slice(-50)
}
