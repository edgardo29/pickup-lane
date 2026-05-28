import { useEffect } from 'react'

export function useModalBodyLock() {
  useEffect(() => {
    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.body.style.overflow = originalOverflow
    }
  }, [])
}

export function useDismissibleModal(onDismiss) {
  useModalBodyLock()

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        onDismiss()
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onDismiss])
}

export function dismissOnBackdropMouseDown(event, onDismiss) {
  if (event.target === event.currentTarget) {
    onDismiss()
  }
}
