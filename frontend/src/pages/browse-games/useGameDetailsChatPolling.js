import { useEffect } from 'react'
import {
  getGameChatReadState,
  loadVisibleChatMessages,
  markGameChatRead,
} from './gameDetailsApi.js'
import {
  getLatestMessageCreatedAt,
  mergeChatMessages,
} from './gameDetailsChat.js'

export function useGameDetailsChatPolling({
  activeChat,
  chatMessagesRef,
  firebaseUser,
  hasUnreadChat,
  isChatOpen,
  setChatMessages,
  setHasUnreadChat,
}) {
  useEffect(() => {
    if (!activeChat?.id || !firebaseUser || isChatOpen) {
      return undefined
    }

    let ignore = false

    async function refreshChatPreview() {
      try {
        if (document.hidden) {
          return
        }

        const readStateResponse = await getGameChatReadState(activeChat.id, firebaseUser)

        if (!ignore) {
          setHasUnreadChat(Boolean(readStateResponse.unread_count))
        }

        if (readStateResponse.unread_count > 0) {
          const messagesResponse = await loadVisibleChatMessages(
            activeChat.id,
            firebaseUser,
            getLatestMessageCreatedAt(chatMessagesRef.current),
          )

          if (!ignore && messagesResponse.length > 0) {
            setChatMessages((currentMessages) => mergeChatMessages(currentMessages, messagesResponse))
          }
        }
      } catch {
        // Chat preview refresh is best-effort; the page should stay usable.
      }
    }

    const intervalId = window.setInterval(refreshChatPreview, 60000)
    return () => {
      ignore = true
      window.clearInterval(intervalId)
    }
  }, [activeChat?.id, chatMessagesRef, firebaseUser, isChatOpen, setChatMessages, setHasUnreadChat])

  useEffect(() => {
    if (!activeChat?.id || !firebaseUser || !isChatOpen) {
      return undefined
    }

    let ignore = false

    async function refreshOpenChat() {
      try {
        if (document.hidden) {
          return
        }

        const afterCreatedAt = getLatestMessageCreatedAt(chatMessagesRef.current)
        const messagesResponse = await loadVisibleChatMessages(activeChat.id, firebaseUser, afterCreatedAt)

        if (!ignore && messagesResponse.length > 0) {
          setChatMessages((currentMessages) => mergeChatMessages(currentMessages, messagesResponse))
          setHasUnreadChat(false)
        }

        if (messagesResponse.length > 0 || hasUnreadChat) {
          await markGameChatRead(activeChat.id, firebaseUser).catch(() => null)
        }
      } catch {
        // Open chat refresh is best-effort; sending and manual refresh still work.
      }
    }

    refreshOpenChat()
    const intervalId = window.setInterval(refreshOpenChat, 5000)

    return () => {
      ignore = true
      window.clearInterval(intervalId)
    }
  }, [
    activeChat?.id,
    chatMessagesRef,
    firebaseUser,
    hasUnreadChat,
    isChatOpen,
    setChatMessages,
    setHasUnreadChat,
  ])
}
