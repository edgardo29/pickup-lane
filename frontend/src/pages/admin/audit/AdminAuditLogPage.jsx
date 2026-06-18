import { useEffect, useMemo, useState } from 'react'
import {
  FileClock,
  FileText,
  Hash,
  RefreshCw,
  Search,
  ShieldCheck,
} from 'lucide-react'
import { AppPageHeader, AppPageShell } from '../../../components/app/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminAuditLog.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import {
  getAdminAction,
  listAdminActions,
} from '../shared/adminApi.js'

const targetFields = [
  ['target_user_id', 'User'],
  ['target_game_id', 'Game'],
  ['target_booking_id', 'Booking'],
  ['target_participant_id', 'Participant'],
  ['target_payment_id', 'Payment'],
  ['target_refund_id', 'Refund'],
  ['target_game_credit_id', 'Credit'],
  ['target_venue_id', 'Venue'],
  ['target_venue_image_id', 'Venue image'],
  ['target_message_id', 'Message'],
  ['target_sub_post_id', 'Need a Sub post'],
  ['target_sub_post_request_id', 'Need a Sub request'],
  ['target_sub_post_position_id', 'Need a Sub position'],
  ['target_sub_chat_message_id', 'Need a Sub chat message'],
  ['target_notification_id', 'Notification'],
  ['target_platform_notice_campaign_id', 'Platform notice campaign'],
  ['target_admin_action_id', 'Audit action'],
  ['target_support_flag_id', 'Support flag'],
]

const limitOptions = [25, 50, 100, 200]

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

function formatDateTime(value) {
  if (!value) {
    return 'No date'
  }

  return dateFormatter.format(new Date(value))
}

function formatActionLabel(value) {
  return String(value || '')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function getTargetEntries(action) {
  return targetFields
    .map(([field, label]) => ({ field, label, value: action?.[field] }))
    .filter((entry) => Boolean(entry.value))
}

function getPrimaryTargetLabel(action) {
  const [primaryTarget] = getTargetEntries(action)

  return primaryTarget ? primaryTarget.label : 'No target'
}

function formatMetadata(metadata) {
  if (!metadata || Object.keys(metadata).length === 0) {
    return ''
  }

  return JSON.stringify(metadata, null, 2)
}

function AdminAuditLogRow({ action, isSelected, onSelect }) {
  const targetLabel = getPrimaryTargetLabel(action)

  return (
    <button
      className={`admin-audit-row ${isSelected ? 'active' : ''}`}
      type="button"
      onClick={() => onSelect(action.id)}
    >
      <span className="admin-audit-row__icon" aria-hidden="true">
        <FileText />
      </span>
      <span className="admin-audit-row__copy">
        <strong>{formatActionLabel(action.action_type)}</strong>
        <span>{targetLabel} - {formatDateTime(action.created_at)}</span>
      </span>
      <em>{action.action_type}</em>
    </button>
  )
}

function AdminAuditTargets({ action }) {
  const targets = getTargetEntries(action)

  if (!targets.length) {
    return <p className="admin-audit-empty">No target references.</p>
  }

  return (
    <div className="admin-audit-targets">
      {targets.map((target) => (
        <div className="admin-audit-target" key={target.field}>
          <span>{target.label}</span>
          <code>{target.value}</code>
        </div>
      ))}
    </div>
  )
}

function AdminAuditDetail({ action, loadState }) {
  const metadataText = useMemo(() => formatMetadata(action?.metadata), [action])

  if (loadState === 'loading') {
    return <p className="admin-audit-empty">Loading audit action.</p>
  }

  if (!action) {
    return (
      <div className="admin-audit-empty-state">
        <strong>No audit action selected</strong>
        <span>Select an action from the log.</span>
      </div>
    )
  }

  return (
    <div className="admin-audit-detail">
      <div className="admin-audit-detail__header">
        <div>
          <FileClock />
          <h2>{formatActionLabel(action.action_type)}</h2>
        </div>
        <em>{formatDateTime(action.created_at)}</em>
      </div>

      <div className="admin-audit-detail__grid">
        <div>
          <span>Action ID</span>
          <code>{action.id}</code>
        </div>
        <div>
          <span>Admin user</span>
          <code>{action.admin_user_id}</code>
        </div>
        {action.idempotency_key && (
          <div>
            <span>Idempotency key</span>
            <code>{action.idempotency_key}</code>
          </div>
        )}
      </div>

      <section className="admin-audit-detail__section">
        <h3>Reason</h3>
        <p>{action.reason || 'No reason recorded.'}</p>
      </section>

      <section className="admin-audit-detail__section">
        <h3>Targets</h3>
        <AdminAuditTargets action={action} />
      </section>

      <section className="admin-audit-detail__section">
        <h3>Metadata</h3>
        {metadataText ? (
          <pre>{metadataText}</pre>
        ) : (
          <p>No metadata recorded.</p>
        )}
      </section>
    </div>
  )
}

function AdminAuditLogPage() {
  const { currentUser } = useAuth()
  const [actionTypeDraft, setActionTypeDraft] = useState('')
  const [actionTypeFilter, setActionTypeFilter] = useState('')
  const [actions, setActions] = useState([])
  const [detailError, setDetailError] = useState('')
  const [detailLoadState, setDetailLoadState] = useState('idle')
  const [limit, setLimit] = useState(100)
  const [listError, setListError] = useState('')
  const [listLoadState, setListLoadState] = useState('loading')
  const [refreshCount, setRefreshCount] = useState(0)
  const [selectedAction, setSelectedAction] = useState(null)
  const [selectedActionId, setSelectedActionId] = useState(null)

  useEffect(() => {
    let isMounted = true

    async function loadActions() {
      if (!currentUser) {
        return
      }

      setListLoadState('loading')
      setListError('')

      try {
        const nextActions = await listAdminActions({
          actionType: actionTypeFilter,
          firebaseUser: currentUser,
          limit,
        })

        if (!isMounted) {
          return
        }

        setActions(nextActions)
        setSelectedActionId((currentSelectedActionId) => (
          nextActions.some((action) => action.id === currentSelectedActionId)
            ? currentSelectedActionId
            : nextActions[0]?.id || null
        ))
        setListLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setActions([])
        setSelectedActionId(null)
        setListError(error.message || 'Audit log could not be loaded.')
        setListLoadState('error')
      }
    }

    loadActions()

    return () => {
      isMounted = false
    }
  }, [actionTypeFilter, currentUser, limit, refreshCount])

  useEffect(() => {
    let isMounted = true

    async function loadSelectedAction() {
      if (!currentUser || !selectedActionId) {
        setSelectedAction(null)
        setDetailError('')
        setDetailLoadState('idle')
        return
      }

      setDetailLoadState('loading')
      setDetailError('')

      try {
        const nextAction = await getAdminAction({
          adminActionId: selectedActionId,
          firebaseUser: currentUser,
        })

        if (!isMounted) {
          return
        }

        setSelectedAction(nextAction)
        setDetailLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setSelectedAction(null)
        setDetailError(error.message || 'Audit action could not be loaded.')
        setDetailLoadState('error')
      }
    }

    loadSelectedAction()

    return () => {
      isMounted = false
    }
  }, [currentUser, selectedActionId])

  function handleFilterSubmit(event) {
    event.preventDefault()
    setActionTypeFilter(actionTypeDraft.trim())
  }

  return (
    <AppPageShell className="admin-page" mainClassName="admin-shell admin-audit-shell">
      <AppPageHeader
        subtitle="Admin"
        title="Audit Log"
      />

      <AdminWorkspaceLayout>
        <div className="admin-audit-layout">
          <section className="admin-audit-panel" aria-label="Audit action list">
            <div className="admin-audit-panel__heading">
              <div>
                <ShieldCheck />
                <h2>Action history</h2>
              </div>
              <em>{actions.length}</em>
            </div>

            <form className="admin-audit-filters" onSubmit={handleFilterSubmit}>
              <label>
                <span>Action type</span>
                <span>
                  <Search />
                  <input
                    value={actionTypeDraft}
                    onChange={(event) => setActionTypeDraft(event.target.value)}
                    placeholder="cancel_game"
                  />
                </span>
              </label>
              <label>
                <span>Limit</span>
                <select
                  value={limit}
                  onChange={(event) => setLimit(Number(event.target.value))}
                >
                  {limitOptions.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </label>
              <button type="submit">
                <Search />
                Apply
              </button>
              <button type="button" onClick={() => setRefreshCount((count) => count + 1)}>
                <RefreshCw />
                Refresh
              </button>
            </form>

            {listError && <p className="admin-audit-alert">{listError}</p>}
            {listLoadState === 'loading' && (
              <p className="admin-audit-empty">Loading audit log.</p>
            )}
            {listLoadState === 'ready' && actions.length === 0 && (
              <div className="admin-audit-empty-state">
                <strong>No audit actions</strong>
                <span>No matching actions were found.</span>
              </div>
            )}
            {listLoadState === 'ready' && actions.length > 0 && (
              <div className="admin-audit-list">
                {actions.map((action) => (
                  <AdminAuditLogRow
                    action={action}
                    isSelected={action.id === selectedActionId}
                    key={action.id}
                    onSelect={setSelectedActionId}
                  />
                ))}
              </div>
            )}
          </section>

          <section className="admin-audit-panel" aria-label="Audit action detail">
            <div className="admin-audit-panel__heading">
              <div>
                <Hash />
                <h2>Action detail</h2>
              </div>
              {selectedAction?.action_type && <em>{selectedAction.action_type}</em>}
            </div>

            {detailError && <p className="admin-audit-alert">{detailError}</p>}
            <AdminAuditDetail action={selectedAction} loadState={detailLoadState} />
          </section>
        </div>
      </AdminWorkspaceLayout>
    </AppPageShell>
  )
}

export default AdminAuditLogPage
