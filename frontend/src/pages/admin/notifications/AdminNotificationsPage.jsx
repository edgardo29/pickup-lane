import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bell,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  FileText,
  Hash,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldCheck,
} from 'lucide-react'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminNotifications.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import {
  getAdminNotification,
  listAdminNotifications,
} from '../shared/adminApi.js'
import {
  ADMIN_NOTIFICATION_RELATED_FIELDS,
  EMPTY_ADMIN_NOTIFICATION_FILTERS,
  NOTIFICATION_ACTION_KEY_OPTIONS,
  NOTIFICATION_CATEGORY_OPTIONS,
  NOTIFICATION_DOMAIN_OPTIONS,
  NOTIFICATION_LIMIT_OPTIONS,
  NOTIFICATION_READ_OPTIONS,
  NOTIFICATION_SOURCE_TYPE_OPTIONS,
  formatAdminNotificationActionState,
  formatAdminNotificationDateTime,
  formatAdminNotificationLabel,
  formatAdminNotificationReadState,
  getAdminNotificationPrimaryReference,
  getAdminNotificationRelatedEntries,
  sanitizeAdminNotificationFilters,
  shortAdminNotificationId,
} from './adminNotificationFormatters.js'

const PRIMARY_FILTER_FIELDS = [
  ['user_id', 'User ID'],
  ['notification_type', 'Type'],
  ['aggregation_key', 'Aggregation key'],
]

const RELATED_FILTER_FIELDS = ADMIN_NOTIFICATION_RELATED_FIELDS

function AdminNotificationsLoading() {
  return (
    <div
      aria-label="Loading notifications"
      className="admin-notifications-loading"
      role="status"
    >
      {Array.from({ length: 5 }).map((_, index) => (
        <div className="admin-notifications-loading__row" key={index}>
          <SkeletonBlock height="0.9rem" rounded width="48%" />
          <SkeletonBlock height="0.72rem" rounded width="68%" />
          <SkeletonBlock height="0.72rem" rounded width="32%" />
        </div>
      ))}
    </div>
  )
}

function AdminNotificationStatusChip({ actionState }) {
  const status = actionState?.status || 'unknown'

  return (
    <span className={`admin-notifications-status admin-notifications-status--${status}`}>
      {formatAdminNotificationActionState(actionState)}
    </span>
  )
}

function AdminNotificationRow({ isSelected, notification, onSelect }) {
  const primaryReference = getAdminNotificationPrimaryReference(notification)
  const rowMeta = [
    formatAdminNotificationLabel(notification.notification_type),
    formatAdminNotificationDateTime(notification.event_at),
  ].join(' - ')

  return (
    <button
      className={`admin-notifications-row ${isSelected ? 'is-active' : ''}`}
      type="button"
      onClick={() => onSelect(notification.id)}
    >
      <span className="admin-notifications-row__icon" aria-hidden="true">
        <Bell />
      </span>
      <span className="admin-notifications-row__copy">
        <strong>{notification.title || 'Inbox update'}</strong>
        <span>{rowMeta}</span>
        <code>User {shortAdminNotificationId(notification.user_id)}</code>
      </span>
      <span className="admin-notifications-row__meta">
        <AdminNotificationStatusChip actionState={notification.action_state} />
        <span>{primaryReference ? primaryReference.label : 'No related entity'}</span>
      </span>
    </button>
  )
}

function AdminNotificationField({ code = false, label, value }) {
  return (
    <div>
      <span>{label}</span>
      {code ? <code>{value || 'None'}</code> : <strong>{value || 'None'}</strong>}
    </div>
  )
}

function AdminNotificationRelatedReferences({ notification }) {
  const relatedEntries = getAdminNotificationRelatedEntries(notification)

  if (!relatedEntries.length) {
    return <p className="admin-notifications-detail-empty">No related records.</p>
  }

  return (
    <div className="admin-notifications-related-list">
      {relatedEntries.map((entry) => (
        <div className="admin-notifications-related-item" key={entry.field}>
          <span>{entry.label}</span>
          <code>{entry.value}</code>
        </div>
      ))}
    </div>
  )
}

function AdminNotificationAuditActions({ actions }) {
  if (!actions?.length) {
    return <p className="admin-notifications-detail-empty">No audit actions linked.</p>
  }

  return (
    <div className="admin-notifications-audit-list">
      {actions.map((action) => (
        <div className="admin-notifications-audit-item" key={action.id}>
          <div>
            <strong>{formatAdminNotificationLabel(action.action_type)}</strong>
            <span>{formatAdminNotificationDateTime(action.created_at)}</span>
          </div>
          <code>{action.id}</code>
          <Link to="/admin/audit">Audit log</Link>
        </div>
      ))}
    </div>
  )
}

function AdminNotificationActionDetail({ notification }) {
  const actionState = notification?.action_state
  const action = notification?.action

  return (
    <section className="admin-notifications-detail-section">
      <h3>Action</h3>
      <div className="admin-notifications-action-card">
        <div>
          <span>State</span>
          <AdminNotificationStatusChip actionState={actionState} />
        </div>
        <div>
          <span>Action key</span>
          <code>{actionState?.action_key || 'None'}</code>
        </div>
        <div>
          <span>Path</span>
          {actionState?.path ? (
            <Link to={actionState.path}>
              <ExternalLink />
              {actionState.path}
            </Link>
          ) : (
            <code>None</code>
          )}
        </div>
        <div>
          <span>Disabled reason</span>
          <code>{actionState?.disabled_reason || 'None'}</code>
        </div>
        {action?.label && (
          <div>
            <span>Action label</span>
            <strong>{action.label}</strong>
          </div>
        )}
      </div>
    </section>
  )
}

function AdminNotificationDetail({ loadState, notification }) {
  const snapshotRows = useMemo(() => [
    ['Subject', notification?.subject_label],
    ['Row subject', notification?.row_subject],
    ['Summary', notification?.summary],
    ['Body', notification?.body],
  ], [notification])

  if (loadState === 'loading') {
    return <p className="admin-notifications-empty">Loading notification.</p>
  }

  if (!notification) {
    return (
      <div className="admin-notifications-empty-state">
        <strong>No notification selected</strong>
        <span>Select a notification from the results.</span>
      </div>
    )
  }

  return (
    <div className="admin-notifications-detail">
      <div className="admin-notifications-detail__header">
        <div>
          <FileText />
          <h2>{notification.title || 'Inbox update'}</h2>
        </div>
        <AdminNotificationStatusChip actionState={notification.action_state} />
      </div>

      <div className="admin-notifications-detail-grid">
        <AdminNotificationField code label="Notification ID" value={notification.id} />
        <AdminNotificationField code label="User ID" value={notification.user_id} />
        <AdminNotificationField
          label="Type"
          value={formatAdminNotificationLabel(notification.notification_type)}
        />
        <AdminNotificationField
          label="Category"
          value={formatAdminNotificationLabel(notification.notification_category)}
        />
        <AdminNotificationField
          label="Domain"
          value={formatAdminNotificationLabel(notification.notification_domain)}
        />
        <AdminNotificationField
          label="Source"
          value={formatAdminNotificationLabel(notification.source_type)}
        />
        <AdminNotificationField
          label="Read state"
          value={formatAdminNotificationReadState(notification)}
        />
        <AdminNotificationField
          label="Event"
          value={formatAdminNotificationDateTime(notification.event_at)}
        />
        <AdminNotificationField
          label="Created"
          value={formatAdminNotificationDateTime(notification.created_at)}
        />
        <AdminNotificationField
          label="Updated"
          value={formatAdminNotificationDateTime(notification.updated_at)}
        />
      </div>

      <AdminNotificationActionDetail notification={notification} />

      <section className="admin-notifications-detail-section">
        <h3>Snapshot</h3>
        <div className="admin-notifications-snapshot-list">
          {snapshotRows.map(([label, value]) => (
            <div key={label}>
              <span>{label}</span>
              <p>{value || 'None'}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="admin-notifications-detail-section">
        <h3>Related Records</h3>
        <AdminNotificationRelatedReferences notification={notification} />
      </section>

      <section className="admin-notifications-detail-section">
        <h3>Audit Actions</h3>
        <AdminNotificationAuditActions actions={notification.audit_actions} />
      </section>
    </div>
  )
}

function AdminNotificationsPage() {
  const { currentUser } = useAuth()
  const [draftFilters, setDraftFilters] = useState(EMPTY_ADMIN_NOTIFICATION_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_ADMIN_NOTIFICATION_FILTERS)
  const [detailError, setDetailError] = useState('')
  const [detailLoadState, setDetailLoadState] = useState('idle')
  const [limit, setLimit] = useState(50)
  const [listError, setListError] = useState('')
  const [listLoadState, setListLoadState] = useState('loading')
  const [notifications, setNotifications] = useState([])
  const [offset, setOffset] = useState(0)
  const [refreshCount, setRefreshCount] = useState(0)
  const [selectedNotification, setSelectedNotification] = useState(null)
  const [selectedNotificationId, setSelectedNotificationId] = useState(null)
  const [totalCount, setTotalCount] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadNotifications() {
      if (!currentUser) {
        return
      }

      setListLoadState('loading')
      setListError('')

      try {
        const response = await listAdminNotifications({
          firebaseUser: currentUser,
          filters: appliedFilters,
          limit,
          offset,
        })

        if (!isMounted) {
          return
        }

        const nextNotifications = response.notifications ?? []
        const nextTotalCount = response.total_count ?? nextNotifications.length

        if (!nextNotifications.length && offset > 0 && nextTotalCount > 0) {
          setOffset(Math.max(0, offset - limit))
          return
        }

        setNotifications(nextNotifications)
        setTotalCount(nextTotalCount)
        setSelectedNotificationId((currentSelectedNotificationId) => (
          nextNotifications.some((notification) => (
            notification.id === currentSelectedNotificationId
          ))
            ? currentSelectedNotificationId
            : nextNotifications[0]?.id || null
        ))
        setListLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setNotifications([])
        setTotalCount(0)
        setSelectedNotificationId(null)
        setListError(error.message || 'Notifications could not be loaded.')
        setListLoadState('error')
      }
    }

    loadNotifications()

    return () => {
      isMounted = false
    }
  }, [appliedFilters, currentUser, limit, offset, refreshCount])

  useEffect(() => {
    let isMounted = true

    async function loadSelectedNotification() {
      if (!currentUser || !selectedNotificationId) {
        setSelectedNotification(null)
        setDetailError('')
        setDetailLoadState('idle')
        return
      }

      setDetailLoadState('loading')
      setDetailError('')

      try {
        const nextNotification = await getAdminNotification({
          firebaseUser: currentUser,
          notificationId: selectedNotificationId,
        })

        if (!isMounted) {
          return
        }

        setSelectedNotification(nextNotification)
        setDetailLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setSelectedNotification(null)
        setDetailError(error.message || 'Notification detail could not be loaded.')
        setDetailLoadState('error')
      }
    }

    loadSelectedNotification()

    return () => {
      isMounted = false
    }
  }, [currentUser, selectedNotificationId])

  function updateDraftFilter(field, value) {
    setDraftFilters((current) => ({
      ...current,
      [field]: value,
    }))
  }

  function handleSearch(event) {
    event.preventDefault()
    setOffset(0)
    setAppliedFilters(sanitizeAdminNotificationFilters(draftFilters))
  }

  function handleReset() {
    setDraftFilters(EMPTY_ADMIN_NOTIFICATION_FILTERS)
    setAppliedFilters(EMPTY_ADMIN_NOTIFICATION_FILTERS)
    setOffset(0)
  }

  function handleLimitChange(event) {
    setLimit(Number(event.target.value))
    setOffset(0)
  }

  const pageStart = totalCount ? offset + 1 : 0
  const pageEnd = Math.min(offset + notifications.length, totalCount)
  const hasPreviousPage = offset > 0
  const hasNextPage = offset + notifications.length < totalCount

  return (
    <>
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'System', 'Notifications']}
        description="Search notification records and inspect delivery and action state."
        icon={Bell}
        title="Notifications"
      >
        <div className="admin-notifications-layout">
          <section
            aria-label="Notification debug list"
            className="admin-notifications-panel"
          >
            <div className="admin-notifications-panel__heading">
              <div>
                <ShieldCheck />
                <h2>Notification Debug</h2>
              </div>
              <span>{listLoadState === 'ready' ? totalCount : 0} results</span>
            </div>

            <form className="admin-notifications-filters" onSubmit={handleSearch}>
              <div className="admin-notifications-filter-grid">
                {PRIMARY_FILTER_FIELDS.map(([field, label]) => (
                  <label key={field}>
                    <span>{label}</span>
                    <input
                      value={draftFilters[field]}
                      onChange={(event) => updateDraftFilter(field, event.target.value)}
                    />
                  </label>
                ))}

                <label>
                  <span>Category</span>
                  <select
                    value={draftFilters.notification_category}
                    onChange={(event) => updateDraftFilter(
                      'notification_category',
                      event.target.value,
                    )}
                  >
                    {NOTIFICATION_CATEGORY_OPTIONS.map((option) => (
                      <option key={option.value || 'all'} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>Domain</span>
                  <select
                    value={draftFilters.notification_domain}
                    onChange={(event) => updateDraftFilter(
                      'notification_domain',
                      event.target.value,
                    )}
                  >
                    {NOTIFICATION_DOMAIN_OPTIONS.map((option) => (
                      <option key={option.value || 'all'} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>Source</span>
                  <select
                    value={draftFilters.source_type}
                    onChange={(event) => updateDraftFilter('source_type', event.target.value)}
                  >
                    {NOTIFICATION_SOURCE_TYPE_OPTIONS.map((option) => (
                      <option key={option.value || 'all'} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>Read state</span>
                  <select
                    value={draftFilters.is_read}
                    onChange={(event) => updateDraftFilter('is_read', event.target.value)}
                  >
                    {NOTIFICATION_READ_OPTIONS.map((option) => (
                      <option key={option.value || 'all'} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>Action key</span>
                  <select
                    value={draftFilters.action_key}
                    onChange={(event) => updateDraftFilter('action_key', event.target.value)}
                  >
                    {NOTIFICATION_ACTION_KEY_OPTIONS.map((option) => (
                      <option key={option.value || 'all'} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="admin-notifications-related-filters">
                {RELATED_FILTER_FIELDS.map(([field, label]) => (
                  <label key={field}>
                    <span>{label}</span>
                    <input
                      value={draftFilters[field]}
                      onChange={(event) => updateDraftFilter(field, event.target.value)}
                    />
                  </label>
                ))}
              </div>

              <div className="admin-notifications-filter-actions">
                <label>
                  <span>Limit</span>
                  <select value={limit} onChange={handleLimitChange}>
                    {NOTIFICATION_LIMIT_OPTIONS.map((option) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                </label>
                <button className="admin-notifications-button" type="submit">
                  <Search />
                  Search
                </button>
                <button
                  className="admin-notifications-button"
                  type="button"
                  onClick={handleReset}
                >
                  <RotateCcw />
                  Reset
                </button>
                <button
                  aria-label="Refresh notifications"
                  className="admin-notifications-button admin-notifications-button--icon"
                  type="button"
                  onClick={() => setRefreshCount((count) => count + 1)}
                >
                  <RefreshCw />
                </button>
              </div>
            </form>

            {listError && (
              <p className="admin-notifications-alert" role="alert">
                {listError}
              </p>
            )}

            {listLoadState === 'loading' && <AdminNotificationsLoading />}
            {listLoadState === 'ready' && notifications.length === 0 && (
              <div className="admin-notifications-empty-state">
                <strong>No notifications found</strong>
                <span>Adjust the filters and search again.</span>
              </div>
            )}
            {listLoadState === 'ready' && notifications.length > 0 && (
              <>
                <div className="admin-notifications-list">
                  {notifications.map((notification) => (
                    <AdminNotificationRow
                      isSelected={notification.id === selectedNotificationId}
                      key={notification.id}
                      notification={notification}
                      onSelect={setSelectedNotificationId}
                    />
                  ))}
                </div>

                <nav
                  aria-label="Notification result pagination"
                  className="admin-notifications-pagination"
                >
                  <span>{pageStart}-{pageEnd} of {totalCount}</span>
                  <div>
                    <button
                      aria-label="Previous notification page"
                      className="admin-notifications-button admin-notifications-button--icon"
                      disabled={!hasPreviousPage}
                      title="Previous page"
                      type="button"
                      onClick={() => setOffset(Math.max(0, offset - limit))}
                    >
                      <ChevronLeft />
                    </button>
                    <button
                      aria-label="Next notification page"
                      className="admin-notifications-button admin-notifications-button--icon"
                      disabled={!hasNextPage}
                      title="Next page"
                      type="button"
                      onClick={() => setOffset(offset + limit)}
                    >
                      <ChevronRight />
                    </button>
                  </div>
                </nav>
              </>
            )}
          </section>

          <section
            aria-label="Notification debug detail"
            className="admin-notifications-panel"
          >
            <div className="admin-notifications-panel__heading">
              <div>
                <Hash />
                <h2>Notification Detail</h2>
              </div>
              {selectedNotification?.notification_type && (
                <span>{formatAdminNotificationLabel(selectedNotification.notification_type)}</span>
              )}
            </div>

            {detailError && (
              <p className="admin-notifications-alert" role="alert">
                {detailError}
              </p>
            )}
            <AdminNotificationDetail
              loadState={detailLoadState}
              notification={selectedNotification}
            />
          </section>
        </div>
      </AdminWorkspaceLayout>
    </>
  )
}

export default AdminNotificationsPage
