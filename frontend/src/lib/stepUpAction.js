export const STEP_UP_REQUIRED_CODE = 'AUTH.RECENT_AUTH_REQUIRED'

export class StepUpCancelledError extends Error {
  constructor(message = 'Identity confirmation was cancelled.') {
    super(message)
    this.name = 'StepUpCancelledError'
    this.code = 'STEP_UP_CANCELLED'
  }
}

export function isStepUpRequiredError(error) {
  return getStepUpErrorCode(error) === STEP_UP_REQUIRED_CODE
}

export function getStepUpErrorCode(error) {
  const code = error?.code || error?.detail?.code || ''
  return typeof code === 'string' ? code : ''
}

export function isStepUpCancelledError(error) {
  return error?.code === 'STEP_UP_CANCELLED'
}

export async function runStepUpProtectedAction({
  action,
  requestStepUp,
}) {
  try {
    return await action()
  } catch (error) {
    if (!isStepUpRequiredError(error)) {
      throw error
    }
  }

  await requestStepUp()
  return action()
}
