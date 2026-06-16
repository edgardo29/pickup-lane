import { createPortal } from 'react-dom'
import {
  CheckCircle2,
  UsersRound,
  X,
} from 'lucide-react'
import { NeedASubPlayerPanel } from './NeedASubPlayerPanel.jsx'
import { NeedASubWaitlistModal } from './NeedASubWaitlistModal.jsx'
import { formatNeedType } from './needASubFormatters.js'
import { useNeedASubRequestGroups } from './useNeedASubRequestGroups.js'
import {
  dismissNeedASubBackdropMouseDown,
  useNeedASubModalDismiss,
} from './useNeedASubModalDismiss.js'

export function NeedASubManageRequestsModal({
  error,
  notice,
  onAcceptRequest,
  onClose,
  onDeclineRequest,
  onRemoveRequest,
  post,
  requests,
}) {
  useNeedASubModalDismiss(onClose)

  const {
    activeRequestStatus,
    requestGroups,
    selectedGroup,
    setActiveRequestStatus,
    setSelectedPositionId,
    setWaitlistModalGroup,
    waitlistModalGroup,
  } = useNeedASubRequestGroups({ post, requests })

  return createPortal(
    <div
      className="need-sub-modal-backdrop need-sub-manage-requests-modal-backdrop"
      role="presentation"
      onMouseDown={(event) => dismissNeedASubBackdropMouseDown(event, onClose)}
    >
      <section
        aria-labelledby="need-sub-manage-requests-title"
        aria-modal="true"
        className="need-sub-manage-requests-modal"
        role="dialog"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="need-sub-manage-requests-modal__header">
          <div className="need-sub-manage-requests-modal__title-row">
            <h2 id="need-sub-manage-requests-title">
              <span className="need-sub-manage-requests-modal__title-icon" aria-hidden="true">
                <UsersRound />
              </span>
              <span>Manage Requests</span>
            </h2>
            {notice && !error && (
              <span className="need-sub-manage-requests-modal__status" aria-live="polite">
                <CheckCircle2 aria-hidden="true" />
                <span>{notice}</span>
              </span>
            )}
          </div>
          <button
            aria-label="Close manage requests"
            className="need-sub-modal-close need-sub-manage-requests-modal__close"
            type="button"
            onClick={onClose}
          >
            <X aria-hidden="true" />
          </button>
        </header>

        {error && (
          <div className="need-sub-alert need-sub-alert--error need-sub-manage-requests-modal__alert">
            {error}
          </div>
        )}

        <div className="need-sub-manage-requests-modal__body">
          <div className="need-sub-manage-requests-modal__spot-field">
            <label htmlFor="need-sub-manage-request-position">Spot type</label>
            <select
              className="need-sub-manage-requests-modal__spot-select"
              disabled={!requestGroups.length}
              id="need-sub-manage-request-position"
              value={selectedGroup?.position.id || ''}
              onChange={(event) => setSelectedPositionId(event.target.value)}
            >
              {requestGroups.map((group) => (
                <option key={group.position.id} value={group.position.id}>
                  {formatManageSpotOption(group)}
                </option>
              ))}
            </select>
          </div>

          {selectedGroup && (
            <NeedASubPlayerPanel
              activeStatus={activeRequestStatus}
              group={selectedGroup}
              onAccept={onAcceptRequest}
              onDecline={onDeclineRequest}
              onRemove={onRemoveRequest}
              onStatusChange={setActiveRequestStatus}
              onViewWaitlist={() => setWaitlistModalGroup(selectedGroup)}
            />
          )}
        </div>

        {waitlistModalGroup && (
          <NeedASubWaitlistModal
            group={waitlistModalGroup}
            onClose={() => setWaitlistModalGroup(null)}
          />
        )}
      </section>
    </div>,
    document.body,
  )
}

function formatManageSpotOption(group) {
  const pendingCount = group.pending.length
  const confirmedCount = Math.max(
    Number(group.position.confirmed_count || 0),
    group.confirmed.length,
  )

  if (pendingCount > 0) {
    return `${formatNeedType(group.position)} · ${pendingCount} pending`
  }

  if (confirmedCount >= Number(group.position.spots_needed || 0)) {
    return `${formatNeedType(group.position)} · Full`
  }

  return formatNeedType(group.position)
}
