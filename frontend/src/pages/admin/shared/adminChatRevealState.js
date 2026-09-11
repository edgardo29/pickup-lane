const CONTEXT_FIELDS = [
  'messageId',
  'offset',
  'parentId',
  'parentKind',
  'view',
  'viewerId',
]

function normalizeContext(context) {
  return {
    messageId: String(context?.messageId || ''),
    offset: Number(context?.offset || 0),
    parentId: String(context?.parentId || ''),
    parentKind: String(context?.parentKind || ''),
    view: String(context?.view || ''),
    viewerId: String(context?.viewerId || ''),
  }
}

function contextsMatch(left, right) {
  const normalizedLeft = normalizeContext(left)
  const normalizedRight = normalizeContext(right)
  return CONTEXT_FIELDS.every((field) => normalizedLeft[field] === normalizedRight[field])
}

export function beginChatRevealRequest(currentRequest, context) {
  return {
    context: normalizeContext(context),
    generation: Number(currentRequest?.generation || 0) + 1,
  }
}

export function invalidateChatRevealRequest(currentRequest) {
  return {
    context: null,
    generation: Number(currentRequest?.generation || 0) + 1,
  }
}

export function shouldApplyChatRevealResponse(activeRequest, request, currentContext) {
  if (!activeRequest?.context || !request?.context) return false
  return (
    activeRequest.generation === request.generation
    && contextsMatch(activeRequest.context, request.context)
    && (!currentContext || contextsMatch(request.context, currentContext))
  )
}
