import { useEffect, useRef } from 'react'

export function useGameDetailsShareAction({
  game,
  setShareCopied,
  title,
  venueName,
}) {
  const shareCopiedTimeoutRef = useRef(null)

  useEffect(() => () => {
    if (shareCopiedTimeoutRef.current) {
      window.clearTimeout(shareCopiedTimeoutRef.current)
    }
  }, [])

  function showShareCopied() {
    setShareCopied(true)

    if (shareCopiedTimeoutRef.current) {
      window.clearTimeout(shareCopiedTimeoutRef.current)
    }

    shareCopiedTimeoutRef.current = window.setTimeout(() => {
      setShareCopied(false)
      shareCopiedTimeoutRef.current = null
    }, 1800)
  }

  async function handleShareGame() {
    if (!game) {
      return
    }

    const shareUrl = `${window.location.origin}/games/${game.id}`
    const shareData = {
      title,
      text: `${title} at ${venueName}`,
      url: shareUrl,
    }

    try {
      setShareCopied(false)

      if (navigator.share) {
        await navigator.share(shareData)
        showShareCopied()
        return
      }

      await navigator.clipboard?.writeText(shareUrl)
      showShareCopied()
    } catch (shareError) {
      if (shareError?.name === 'AbortError') {
        return
      }
    }
  }

  return { handleShareGame }
}
