import { useCallback, useEffect, useRef, useState } from 'react'
import {
  openGameChat,
  sendGameChatMessage,
} from './gameDetailsApi.js'
import { GAME_CHAT_MESSAGE_MAX_LENGTH } from './gameDetailsConstants.js'
import { useGameDetailsChatPolling } from './useGameDetailsChatPolling.js'

export function useGameDetailsChat({
  canOpenGameChat,
  firebaseUser,
  gameId,
  onJoinNotice,
  onShareCopiedChange,
}) {
  const [activeChat, setActiveChat] = useState(null)
  const [chatMessages, setChatMessages] = useState([])
  const [chatDraft, setChatDraft] = useState('')
  const [chatError, setChatError] = useState('')
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [isSendingChatMessage, setIsSendingChatMessage] = useState(false)
  const [hasUnreadChat, setHasUnreadChat] = useState(false)
  const chatMessagesRef = useRef([])

  useEffect(() => {
    chatMessagesRef.current = chatMessages
  }, [chatMessages])

  useGameDetailsChatPolling({
    activeChat,
    chatMessagesRef,
    firebaseUser,
    hasUnreadChat,
    isChatOpen,
    setChatMessages,
    setHasUnreadChat,
  })

  function resetChatState() {
    setIsChatOpen(false)
    setActiveChat(null)
    setChatDraft('')
    setChatError('')
    setIsSendingChatMessage(false)
    setHasUnreadChat(false)
  }

  const hydrateChatState = useCallback(function hydrateChatState({
    activeChat: nextActiveChat,
    chatMessages: nextChatMessages,
    hasUnreadChat: nextHasUnreadChat,
  }) {
    setActiveChat(nextActiveChat)
    setChatMessages(nextChatMessages)
    setHasUnreadChat(nextHasUnreadChat)
  }, [])

  function clearChatState() {
    setActiveChat(null)
    setChatMessages([])
    setHasUnreadChat(false)
    setIsChatOpen(false)
  }

  async function handleOpenChat() {
    if (!canOpenGameChat || !firebaseUser) {
      return
    }

    onShareCopiedChange(false)
    setChatError('')

    try {
      const { chat, messages } = await openGameChat({ activeChat, firebaseUser, gameId })

      setActiveChat(chat)
      setIsChatOpen(true)
      setHasUnreadChat(false)
      setChatMessages(messages)
    } catch (requestError) {
      onJoinNotice(
        requestError instanceof Error ? requestError.message : 'Unable to open chat.',
      )
    }
  }

  async function handleSendChatMessage(event) {
    event.preventDefault()

    if (!activeChat?.id || !firebaseUser) {
      return
    }

    const trimmedMessage = chatDraft.trim()
    if (!trimmedMessage) {
      setChatError('Type a message first.')
      return
    }

    if (trimmedMessage.length > GAME_CHAT_MESSAGE_MAX_LENGTH) {
      setChatError(`Keep messages under ${GAME_CHAT_MESSAGE_MAX_LENGTH} characters.`)
      return
    }

    setIsSendingChatMessage(true)
    setChatError('')

    try {
      const newMessage = await sendGameChatMessage(activeChat.id, firebaseUser, trimmedMessage)

      setChatMessages((currentMessages) => [...currentMessages, newMessage].slice(-50))
      setChatDraft('')
      setHasUnreadChat(false)
    } catch (requestError) {
      setChatError(
        requestError instanceof Error ? requestError.message : 'Unable to send message.',
      )
    } finally {
      setIsSendingChatMessage(false)
    }
  }

  return {
    chatDraft,
    chatError,
    chatMessages,
    clearChatState,
    closeChat: () => setIsChatOpen(false),
    handleOpenChat,
    handleSendChatMessage,
    hasUnreadChat,
    hydrateChatState,
    isChatOpen,
    isSendingChatMessage,
    resetChatState,
    setChatDraft,
  }
}
