import { useEffect, useState } from 'react'

export function useGameDetailsUiState() {
  const [activeImageIndex, setActiveImageIndex] = useState(0)
  const [joinNotice, setJoinNotice] = useState('')
  const [shareCopied, setShareCopied] = useState(false)
  const [isJoining, setIsJoining] = useState(false)
  const [isLeaving, setIsLeaving] = useState(false)
  const [isAddingHostGuest, setIsAddingHostGuest] = useState(false)
  const [isUpdatingGuests, setIsUpdatingGuests] = useState(false)
  const [isCancellingGame, setIsCancellingGame] = useState(false)
  const [isHostGuestModalOpen, setIsHostGuestModalOpen] = useState(false)
  const [isCancelGameModalOpen, setIsCancelGameModalOpen] = useState(false)
  const [isLeaveModalOpen, setIsLeaveModalOpen] = useState(false)
  const [isPlayerListOpen, setIsPlayerListOpen] = useState(false)
  const [activePlayerTab, setActivePlayerTab] = useState('going')
  const [nowMs, setNowMs] = useState(null)

  useEffect(() => {
    function updateNow() {
      setNowMs(Date.now())
    }

    updateNow()
    const intervalId = window.setInterval(updateNow, 30000)

    return () => window.clearInterval(intervalId)
  }, [])

  function resetUiState() {
    setJoinNotice('')
    setShareCopied(false)
    setIsJoining(false)
    setIsLeaving(false)
    setIsAddingHostGuest(false)
    setIsCancellingGame(false)
    setIsHostGuestModalOpen(false)
    setIsCancelGameModalOpen(false)
    setIsLeaveModalOpen(false)
    setIsPlayerListOpen(false)
    setActivePlayerTab('going')
    setActiveImageIndex(0)
  }

  return {
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
  }
}
