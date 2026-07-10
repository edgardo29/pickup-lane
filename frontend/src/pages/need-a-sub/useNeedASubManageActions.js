import {
  acceptNeedASubRequest,
  cancelNeedASubPost,
  cancelNeedASubRequestByOwner,
  declineNeedASubRequest,
} from './needASubApi.js'

export function useNeedASubManageActions({
  currentUser,
  loadManageView,
  navigate,
  post,
  setError,
  setNotice,
}) {
  async function runAction(action, successMessage) {
    try {
      await action()
      setNotice(successMessage)
      setError('')
      await loadManageView()
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : 'Unable to update post.')
    }
  }

  async function cancelPost() {
    if (!post) {
      return
    }

    try {
      await cancelNeedASubPost(currentUser, post.id, 'Canceled by host.')
      navigate('/need-a-sub', {
        replace: true,
        state: { needASubNotice: 'Post cancelled.' },
      })
    } catch (cancelError) {
      setError(cancelError instanceof Error ? cancelError.message : 'Unable to cancel post.')
      setNotice('')
    }
  }

  return {
    cancelPost,
    handleAcceptRequest: (request) =>
      runAction(
        () => acceptNeedASubRequest(currentUser, request.id),
        'Player confirmed.',
      ),
    handleDeclineRequest: (request) =>
      runAction(
        () => declineNeedASubRequest(currentUser, request.id),
        'Request declined.',
      ),
    handleRemoveRequest: (request) =>
      runAction(
        () => cancelNeedASubRequestByOwner(currentUser, request.id),
        'Player removed.',
      ),
  }
}
