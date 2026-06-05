import { useEffect } from 'react'

export function useNeedASubModalDismiss(onDismiss) {
  useEffect(() => {
    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onDismiss()
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.body.style.overflow = originalOverflow
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [onDismiss])
}

export function dismissNeedASubBackdropMouseDown(event, onDismiss) {
  if (event.target === event.currentTarget) {
    onDismiss()
  }
}
