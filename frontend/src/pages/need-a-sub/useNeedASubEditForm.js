import { useMemo, useState } from 'react'
import { updateNeedASubPost } from './needASubApi.js'
import { getDefaultPositions, getNextPosition } from './needASubData.js'
import { buildNeedASubPayload, hydrateNeedASubForm } from './needASubPayloads.js'
import { validateNeedASubForm } from './needASubValidation.js'

export function useNeedASubEditForm({
  currentUser,
  loadManageView,
  post,
  setError,
  setNotice,
  setPost,
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [isSavingEdit, setIsSavingEdit] = useState(false)
  const [editForm, setEditForm] = useState(null)
  const [editError, setEditError] = useState('')
  const totalEditSpotsNeeded = useMemo(
    () => (editForm?.positions || []).reduce((sum, position) => sum + Number(position.spots_needed || 0), 0),
    [editForm?.positions],
  )

  function beginEdit() {
    setEditForm(hydrateNeedASubForm(post))
    setEditError('')
    setNotice('')
    setError('')
    setIsEditing(true)
  }

  function cancelEdit() {
    setIsEditing(false)
  }

  function updateEditField(field, value) {
    setEditError('')
    setEditForm((currentForm) => ({ ...currentForm, [field]: value }))
  }

  function updateEditGamePlayerGroup(value) {
    setEditError('')
    setEditForm((currentForm) => ({
      ...currentForm,
      gamePlayerGroup: value,
      positions: getDefaultPositions(value),
    }))
  }

  function updateEditPosition(index, field, value) {
    setEditError('')
    setEditForm((currentForm) => ({
      ...currentForm,
      positions: currentForm.positions.map((position, currentIndex) =>
        currentIndex === index
          ? { ...position, [field]: field === 'spots_needed' ? Number(value) : value }
          : position,
      ),
    }))
  }

  function addEditPosition() {
    setEditForm((currentForm) => ({
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

  function removeEditPosition(index) {
    setEditForm((currentForm) => ({
      ...currentForm,
      positions: currentForm.positions
        .filter((_, currentIndex) => currentIndex !== index)
        .map((position, sortOrder) => ({ ...position, sort_order: sortOrder })),
    }))
  }

  async function submitEdit(event) {
    event.preventDefault()

    const validationError = validateNeedASubForm(editForm)
    if (validationError) {
      setEditError(validationError)
      return
    }

    setIsSavingEdit(true)
    try {
      const payload = buildNeedASubPayload(editForm, totalEditSpotsNeeded)
      const updatedPost = await updateNeedASubPost(currentUser, post.id, payload)
      setPost(updatedPost)
      setNotice('Post updated.')
      setError('')
      setEditError('')
      setIsEditing(false)
      await loadManageView()
    } catch (editSubmitError) {
      setEditError(editSubmitError instanceof Error ? editSubmitError.message : 'Unable to update post.')
    } finally {
      setIsSavingEdit(false)
    }
  }

  return {
    addEditPosition,
    beginEdit,
    cancelEdit,
    editError,
    editForm,
    isEditing,
    isSavingEdit,
    removeEditPosition,
    submitEdit,
    totalEditSpotsNeeded,
    updateEditField,
    updateEditGamePlayerGroup,
    updateEditPosition,
  }
}
