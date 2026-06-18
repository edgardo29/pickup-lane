import { useCallback, useEffect, useState } from 'react'
import {
  ensureNeedASubChat,
  getNeedASubChat,
  listNeedASubChatMessages,
  markNeedASubChatRead,
  sendNeedASubChatMessage,
} from './needASubApi.js'

const SUB_CHAT_MESSAGE_MAX_LENGTH = 300
const SUB_CHAT_MESSAGE_PAGE_SIZE = 50

export function useNeedASubChat({
  canOpenSubChat,
  firebaseUser,
  onError,
  postId,
}) {
  const [activeChat, setActiveChat] = useState(null)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [isOpening, setIsOpening] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [isLoadingOlder, setIsLoadingOlder] = useState(false)
  const [hasMoreMessages, setHasMoreMessages] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)

  useEffect(() => {
    let isCancelled = false

    async function loadExistingChat() {
      if (!canOpenSubChat || !firebaseUser || !postId) {
        setActiveChat(null)
        setMessages([])
        setDraft('')
        setError('')
        setIsOpen(false)
        setUnreadCount(0)
        return
      }

      try {
        const chat = await getNeedASubChat(firebaseUser, postId)

        if (isCancelled) {
          return
        }

        setActiveChat(chat)
        setUnreadCount(Number(chat?.unread_count || 0))
      } catch {
        if (!isCancelled) {
          setActiveChat(null)
          setUnreadCount(0)
        }
      }
    }

    loadExistingChat()

    return () => {
      isCancelled = true
    }
  }, [canOpenSubChat, firebaseUser, postId])

  const openChat = useCallback(async function openChat() {
    if (!canOpenSubChat || !firebaseUser || !postId) {
      return
    }

    setIsOpening(true)
    setError('')
    onError?.('')

    try {
      const chat = activeChat?.id
        ? activeChat
        : await ensureNeedASubChat(firebaseUser, postId)
      const latestMessages = await listNeedASubChatMessages(firebaseUser, postId, {
        limit: SUB_CHAT_MESSAGE_PAGE_SIZE,
      }).catch(() => [])

      await markNeedASubChatRead(firebaseUser, postId)

      setActiveChat(chat)
      setMessages(latestMessages)
      setHasMoreMessages(latestMessages.length === SUB_CHAT_MESSAGE_PAGE_SIZE)
      setUnreadCount(0)
      setIsOpen(true)
    } catch (requestError) {
      onError?.(
        requestError instanceof Error ? requestError.message : 'Unable to open chat.',
      )
    } finally {
      setIsOpening(false)
    }
  }, [activeChat, canOpenSubChat, firebaseUser, onError, postId])

  async function loadOlderMessages() {
    if (!firebaseUser || !postId || messages.length === 0 || isLoadingOlder) {
      return
    }

    const firstMessage = messages[0]
    if (!firstMessage?.created_at) {
      setHasMoreMessages(false)
      return
    }

    setIsLoadingOlder(true)
    setError('')

    try {
      const olderMessages = await listNeedASubChatMessages(firebaseUser, postId, {
        beforeCreatedAt: firstMessage.created_at,
        limit: SUB_CHAT_MESSAGE_PAGE_SIZE,
      })

      setMessages((currentMessages) => mergeMessages(olderMessages, currentMessages))
      setHasMoreMessages(olderMessages.length === SUB_CHAT_MESSAGE_PAGE_SIZE)
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : 'Unable to load older messages.',
      )
    } finally {
      setIsLoadingOlder(false)
    }
  }

  async function sendMessage(event) {
    event.preventDefault()

    if (!activeChat?.id || !firebaseUser || isSending) {
      return
    }

    const trimmedMessage = draft.trim()
    if (!trimmedMessage) {
      setError('Type a message first.')
      return
    }

    if (trimmedMessage.length > SUB_CHAT_MESSAGE_MAX_LENGTH) {
      setError(`Keep messages under ${SUB_CHAT_MESSAGE_MAX_LENGTH} characters.`)
      return
    }

    setIsSending(true)
    setError('')

    try {
      const newMessage = await sendNeedASubChatMessage(
        firebaseUser,
        postId,
        activeChat.id,
        trimmedMessage,
      )

      setMessages((currentMessages) =>
        mergeMessages(currentMessages, [newMessage]).slice(-SUB_CHAT_MESSAGE_PAGE_SIZE),
      )
      setDraft('')
      setUnreadCount(0)
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : 'Unable to send message.',
      )
    } finally {
      setIsSending(false)
    }
  }

  return {
    closeChat: () => setIsOpen(false),
    draft,
    error,
    hasMoreMessages,
    isLoadingOlder,
    isOpen,
    isOpening,
    isSending,
    loadOlderMessages,
    maxLength: SUB_CHAT_MESSAGE_MAX_LENGTH,
    messages,
    openChat,
    sendMessage,
    setDraft,
    unreadCount,
  }
}

function mergeMessages(firstList, secondList) {
  const messageMap = new Map()
  const allMessages = [...firstList, ...secondList]

  allMessages.forEach((message) => {
    if (message?.id) {
      messageMap.set(message.id, message)
    }
  })

  return Array.from(messageMap.values()).sort((left, right) => {
    const leftTime = new Date(left.created_at || 0).getTime()
    const rightTime = new Date(right.created_at || 0).getTime()

    if (leftTime !== rightTime) {
      return leftTime - rightTime
    }

    return String(left.id).localeCompare(String(right.id))
  })
}
