import { useCallback, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'

function storageKey(userId, destination) {
  return `pickup-lane:verification-form:${userId}:${destination}`
}

function restoreForm(userId, destination, initialForm, shouldRestore) {
  if (!userId || !shouldRestore) return initialForm
  try {
    const saved = JSON.parse(window.localStorage.getItem(storageKey(userId, destination)))
    if (saved?.userId !== userId || saved?.destination !== destination) return initialForm
    // Restore only the form's own fields, never arbitrary stored properties.
    if (!matchesFormShape(saved.form, initialForm)) return initialForm
    return Object.fromEntries(Object.keys(initialForm).map((key) => [key, saved.form[key]]))
  } catch { return initialForm }
}

function matchesFormShape(value, initial) {
  if (Array.isArray(initial)) {
    return Array.isArray(value) && value.every((entry) => matchesFormShape(entry, initial[0]))
  }
  if (initial && typeof initial === 'object') {
    return value !== null && typeof value === 'object' && !Array.isArray(value)
      && Object.keys(initial).every((key) => matchesFormShape(value[key], initial[key]))
  }
  return typeof value === typeof initial || (
    typeof initial === 'string' && typeof value === 'number' && Number.isFinite(value)
  )
}

// A one-time bridge for an explicitly requested verification email, not a saved draft.
export function useVerificationFormState({ userId, destination, initialForm, enabled = true }) {
  const location = useLocation()
  const shouldRestore = enabled && new URLSearchParams(location.search).get('verification') === 'return'
  const [state, setState] = useState(() => ({
    owner: userId,
    form: restoreForm(userId, destination, initialForm, shouldRestore),
  }))
  const form = state.owner === userId ? state.form : initialForm

  // Reset this hook's own state before React renders a different account's form.
  if (state.owner !== userId) {
    setState({ owner: userId, form: restoreForm(userId, destination, initialForm, shouldRestore) })
  }

  useEffect(() => {
    if (userId && shouldRestore) {
      try { window.localStorage.removeItem(storageKey(userId, destination)) } catch { /* Storage may be unavailable. */ }
    }
  }, [userId, destination, initialForm, shouldRestore])

  const setForm = useCallback((value) => {
    setState((current) => ({
      owner: userId,
      form: typeof value === 'function'
        ? value(current.owner === userId ? current.form : initialForm)
        : value,
    }))
  }, [userId, initialForm])

  function preserveForVerification() {
    if (!userId || !enabled) return
    try {
      window.localStorage.setItem(storageKey(userId, destination), JSON.stringify({
        userId, destination, form,
      }))
    } catch { /* Keep the in-memory form when browser storage is unavailable. */ }
  }

  return { form, setForm, preserveForVerification }
}
