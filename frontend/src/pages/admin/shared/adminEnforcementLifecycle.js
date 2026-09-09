export function isAdminEnforcementConflict(error) {
  return error?.status === 409
}

export function recoverAdminEnforcementConflict(
  error,
  { clearStaleState, reloadAuthoritativeState },
) {
  if (!isAdminEnforcementConflict(error)) {
    return false
  }

  clearStaleState?.()
  reloadAuthoritativeState?.()
  return true
}

export async function runAdminEnforcementMutation({
  clearStaleState,
  execute,
  onError,
  onPendingChange,
  onSuccess,
  reloadAuthoritativeState,
}) {
  onPendingChange?.(true)
  try {
    const result = await execute()
    onSuccess?.(result)
    return { outcome: 'success', result }
  } catch (error) {
    if (
      recoverAdminEnforcementConflict(error, {
        clearStaleState,
        reloadAuthoritativeState,
      })
    ) {
      return { outcome: 'conflict' }
    }
    onError?.(error)
    return { error, outcome: 'error' }
  } finally {
    onPendingChange?.(false)
  }
}
