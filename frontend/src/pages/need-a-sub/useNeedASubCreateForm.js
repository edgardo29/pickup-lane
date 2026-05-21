import { useMemo, useState } from 'react'
import { createNeedASubPost } from './needASubApi.js'
import { buildInitialNeedASubForm, getDefaultPositions, getNextPosition } from './needASubData.js'
import { buildNeedASubPayload } from './needASubPayloads.js'
import { validateNeedASubForm } from './needASubValidation.js'

export function useNeedASubCreateForm({
  currentUser,
  navigate,
  refreshNeedASub,
  setActivePanel,
  setError,
  setNotice,
  setPostView,
}) {
  const [form, setForm] = useState(() => buildInitialNeedASubForm())
  const [isCreating, setIsCreating] = useState(false)
  const [formError, setFormError] = useState('')
  const totalSpotsNeeded = useMemo(
    () => form.positions.reduce((sum, position) => sum + Number(position.spots_needed || 0), 0),
    [form.positions],
  )

  function clearCreateFeedback() {
    setNotice('')
    setError('')
    setFormError('')
  }

  function updateField(field, value) {
    clearCreateFeedback()
    setForm((currentForm) => ({ ...currentForm, [field]: value }))
  }

  function updateGamePlayerGroup(value) {
    clearCreateFeedback()
    setForm((currentForm) => ({
      ...currentForm,
      gamePlayerGroup: value,
      positions: getDefaultPositions(value),
    }))
  }

  function updatePosition(index, field, value) {
    clearCreateFeedback()
    setForm((currentForm) => ({
      ...currentForm,
      positions: currentForm.positions.map((position, currentIndex) =>
        currentIndex === index
          ? { ...position, [field]: field === 'spots_needed' ? Number(value) : value }
          : position,
      ),
    }))
  }

  function addPosition() {
    setForm((currentForm) => ({
      ...currentForm,
      positions: [
        ...currentForm.positions,
        {
          ...getNextPosition(currentForm.positions, currentForm.gamePlayerGroup),
          spots_needed: 1,
          sort_order: currentForm.positions.length,
        },
      ],
    }))
  }

  function removePosition(index) {
    setForm((currentForm) => ({
      ...currentForm,
      positions: currentForm.positions
        .filter((_, currentIndex) => currentIndex !== index)
        .map((position, sortOrder) => ({ ...position, sort_order: sortOrder })),
    }))
  }

  async function submitPost(event) {
    event.preventDefault()

    if (!currentUser) {
      navigate('/sign-in', { state: { from: '/need-a-sub' } })
      return
    }

    const validationError = validateNeedASubForm(form)
    if (validationError) {
      setFormError(validationError)
      return
    }

    setIsCreating(true)
    setError('')
    setNotice('')

    try {
      const payload = buildNeedASubPayload(form, totalSpotsNeeded)
      await createNeedASubPost(currentUser, payload)
      setPostView('mine')
      setForm(buildInitialNeedASubForm())
      setActivePanel('browse')
      setNotice('Post published.')
      await refreshNeedASub({ showLoading: true })
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to create post.')
    } finally {
      setIsCreating(false)
    }
  }

  return {
    addPosition,
    clearCreateFeedback,
    form,
    formError,
    isCreating,
    removePosition,
    submitPost,
    totalSpotsNeeded,
    updateField,
    updateGamePlayerGroup,
    updatePosition,
  }
}
