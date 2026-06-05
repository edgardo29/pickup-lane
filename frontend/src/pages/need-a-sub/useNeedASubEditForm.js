import { useMemo, useState } from 'react'
import { updateNeedASubPost } from './needASubApi.js'
import {
  buildAddedPositions,
  gamePlayerGroupCreatesPositionConflict,
} from './needASubData.js'
import { buildNeedASubPayload, hydrateNeedASubForm } from './needASubPayloads.js'
import {
  getMinimumEditableSpots,
  hasActivePositionRequests,
} from './needASubSelectors.js'
import { validateNeedASubForm } from './needASubValidation.js'

export function useNeedASubEditForm({
  currentUser,
  onSaved,
  post,
}) {
  const initialEditForm = hydrateNeedASubForm(post)
  const [isSavingEdit, setIsSavingEdit] = useState(false)
  const [editForm, setEditForm] = useState(() => initialEditForm)
  const [baselineForm] = useState(() => initialEditForm)
  const [editError, setEditError] = useState('')

  const totalEditSpotsNeeded = useMemo(
    () => (editForm?.positions || []).reduce((sum, position) => sum + Number(position.spots_needed || 0), 0),
    [editForm?.positions],
  )
  const hasUnsavedChanges = useMemo(
    () => Boolean(editForm && baselineForm && JSON.stringify(editForm) !== JSON.stringify(baselineForm)),
    [baselineForm, editForm],
  )

  function updateEditField(field, value) {
    setEditError('')
    setEditForm((currentForm) => ({ ...currentForm, [field]: value }))
  }

  function updateEditGamePlayerGroup(value) {
    setEditError('')
    setEditForm((currentForm) => {
      if (gamePlayerGroupCreatesPositionConflict(value, currentForm.positions)) {
        setEditError('Sub requirements must match the selected player group.')
        return currentForm
      }

      return {
        ...currentForm,
        gamePlayerGroup: value,
      }
    })
  }

  function updateEditPosition(index, field, value) {
    setEditError('')
    setEditForm((currentForm) => ({
      ...currentForm,
      positions: currentForm.positions.map((position, currentIndex) => {
        if (currentIndex !== index) {
          return position
        }

        if (
          hasActivePositionRequests(position) &&
          ['position_label', 'player_group'].includes(field)
        ) {
          return position
        }

        if (field === 'spots_needed') {
          return {
            ...position,
            spots_needed: Math.max(getMinimumEditableSpots(position), Number(value)),
          }
        }

        return { ...position, [field]: value }
      }),
    }))
  }

  function addEditPosition() {
    setEditForm((currentForm) => ({
      ...currentForm,
      positions: buildAddedPositions(currentForm),
    }))
  }

  function removeEditPosition(index) {
    setEditForm((currentForm) => ({
      ...currentForm,
      positions: currentForm.positions
        .filter((position, currentIndex) =>
          currentIndex !== index || hasActivePositionRequests(position)
        )
        .map((position, sortOrder) => ({ ...position, sort_order: sortOrder })),
    }))
  }

  function isGamePlayerGroupOptionDisabled(value) {
    return editForm
      ? gamePlayerGroupCreatesPositionConflict(value, editForm.positions)
      : false
  }

  async function submitEdit(event) {
    event?.preventDefault?.()

    const validationError = validateNeedASubForm(editForm)
    if (validationError) {
      setEditError(validationError)
      return
    }

    setIsSavingEdit(true)
    try {
      const payload = buildNeedASubPayload(editForm, totalEditSpotsNeeded)
      const updatedPost = await updateNeedASubPost(currentUser, post.id, payload)
      setEditError('')
      onSaved?.(updatedPost)
    } catch (editSubmitError) {
      setEditError(editSubmitError instanceof Error ? editSubmitError.message : 'Unable to update post.')
    } finally {
      setIsSavingEdit(false)
    }
  }

  return {
    addEditPosition,
    baselineForm,
    editError,
    editForm,
    hasUnsavedChanges,
    isGamePlayerGroupOptionDisabled,
    isSavingEdit,
    removeEditPosition,
    submitEdit,
    totalEditSpotsNeeded,
    updateEditField,
    updateEditGamePlayerGroup,
    updateEditPosition,
  }
}
