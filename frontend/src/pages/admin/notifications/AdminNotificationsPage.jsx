import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  Bell,
  Copy,
  ExternalLink,
  FileText,
  Search,
  ShieldCheck,
  X,
} from 'lucide-react'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/inbox/InboxPage.css'
import '../../../styles/admin/AdminNotifications.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import {
  getAdminNotification,
  listAdminLookupUsers,
  listAdminNotifications,
} from '../shared/adminApi.js'
import InboxRow from '../../inbox/InboxRow.jsx'
import {
  beginAdminNotificationRequest,
  buildAdminNotificationClearedCollectionState,
  buildAdminNotificationCollectionFilters,
  cancelAdminNotificationRequest,
  formatAdminNotificationActionState,
  formatAdminNotificationDateTime,
  formatAdminNotificationLabel,
  formatAdminNotificationReadState,
  shouldApplyAdminNotificationResponse,
} from './adminNotificationFormatters.js'

const USER_SEARCH_DEBOUNCE_MS = 300
const USER_SEARCH_MIN_LENGTH = 3
const USER_SEARCH_LIMIT = 10

function AdminNotificationsLoading() {
  return (
    <div
      aria-label="Loading notifications"
      className="admin-notifications-loading"
      role="status"
    >
      {Array.from({ length: 4 }).map((_, index) => (
        <div className="admin-notifications-loading__row" key={index}>
          <SkeletonBlock height="0.9rem" rounded width="48%" />
          <SkeletonBlock height="0.72rem" rounded width="68%" />
          <SkeletonBlock height="0.72rem" rounded width="32%" />
        </div>
      ))}
    </div>
  )
}

function isAbortError(error) {
  return error?.name === 'AbortError'
}

async function writeClipboardText(value) {
  const text = String(value || '')

  if (!text) {
    return false
  }

  if (globalThis.navigator?.clipboard?.writeText) {
    await globalThis.navigator.clipboard.writeText(text)
    return true
  }

  if (!globalThis.document?.body) {
    return false
  }

  const textArea = globalThis.document.createElement('textarea')
  textArea.value = text
  textArea.setAttribute('readonly', '')
  textArea.style.position = 'fixed'
  textArea.style.opacity = '0'
  globalThis.document.body.append(textArea)
  textArea.select()

  try {
    return globalThis.document.execCommand('copy')
  } finally {
    textArea.remove()
  }
}

function recipientDisplayName(user) {
  if (!user) {
    return ''
  }

  return user.display_name || user.email || user.id
}

function AdminNotificationRecipientToken({ onClear, user }) {
  return (
    <div className="admin-notifications-user-token">
      <div>
        <strong>{recipientDisplayName(user)}</strong>
        <span>{user.email || user.id}</span>
      </div>
      <button aria-label="Clear selected recipient" type="button" onClick={onClear}>
        <X aria-hidden="true" />
      </button>
    </div>
  )
}

function AdminNotificationRow({ notification, onSelect }) {
  return (
    <InboxRow
      notification={notification}
      showMeta
      showNewBadge={false}
      showReadIndicator={false}
      showRelativeTime={false}
      showUnreadState={false}
      onOpenNotification={() => onSelect(notification.id)}
    />
  )
}

function AdminNotificationField({ code = false, label, value }) {
  return (
    <div className="admin-notifications-detail-fact">
      <span>{label}</span>
      {code ? <code>{value || 'None'}</code> : <strong>{value || 'None'}</strong>}
    </div>
  )
}

function AdminNotificationMessageSnapshot({ notification }) {
  const rowSubject = notification?.row_subject || notification?.subject_label || ''
  const message = notification?.body || notification?.summary || ''

  return (
    <section className="admin-notifications-detail-section">
      <h3>Message</h3>
      <div className="admin-notifications-message">
        {rowSubject && (
          <div>
            <span>Context</span>
            <p>{rowSubject}</p>
          </div>
        )}
        <div>
          <span>Message</span>
          <p>{message || 'None'}</p>
        </div>
      </div>
    </section>
  )
}

function AdminNotificationSupportDetails({ notification, recipient }) {
  const [copied, setCopied] = useState(false)
  const actionState = notification?.action_state

  async function copyNotificationId() {
    if (!notification.id) {
      return
    }

    try {
      setCopied(await writeClipboardText(notification.id))
    } catch {
      setCopied(false)
    }
  }

  return (
    <section className="admin-notifications-detail-section">
      <h3>Support details</h3>
      <div className="admin-notifications-detail-facts">
        {recipient && (
          <AdminNotificationField
            label="Recipient"
            value={`${recipientDisplayName(recipient)}${recipient.email ? ` - ${recipient.email}` : ''}`}
          />
        )}
        <AdminNotificationField
          label="Read status"
          value={formatAdminNotificationReadState(notification)}
        />
        {notification.read_at && (
          <AdminNotificationField
            label="Read at"
            value={formatAdminNotificationDateTime(notification.read_at)}
          />
        )}
        <AdminNotificationField
          label="Event time"
          value={formatAdminNotificationDateTime(notification.event_at)}
        />
        <div className="admin-notifications-detail-fact admin-notifications-detail-fact--destination">
          <span>Destination</span>
          <div>
            <strong>{formatAdminNotificationActionState(actionState)}</strong>
            {actionState?.path && (
              <Link to={actionState.path}>
                <ExternalLink />
                Open destination
              </Link>
            )}
          </div>
        </div>
        <div className="admin-notifications-detail-fact admin-notifications-detail-fact--copy">
          <span>Notification ID</span>
          <code>{notification.id}</code>
          <button type="button" onClick={copyNotificationId}>
            <Copy aria-hidden="true" />
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>
    </section>
  )
}

function AdminNotificationDetail({ loadState, notification, recipient }) {
  if (loadState === 'loading') {
    return <p className="admin-notifications-empty">Loading notification.</p>
  }

  if (loadState === 'error' && !notification) {
    return null
  }

  if (!notification) {
    return null
  }

  return (
    <div className="admin-notifications-detail">
      <AdminNotificationMessageSnapshot notification={notification} />
      <AdminNotificationSupportDetails notification={notification} recipient={recipient} />
    </div>
  )
}

function AdminNotificationDetailModal({
  detailError,
  loadState,
  notification,
  onClose,
  recipient,
}) {
  const title = notification?.title || 'Notification detail'
  const sourceLabel = notification?.source_label
    || (notification?.source_type ? formatAdminNotificationLabel(notification.source_type) : '')

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div
      className="admin-notifications-modal-backdrop"
      role="presentation"
      onClick={onClose}
    >
      <section
        aria-labelledby="admin-notification-detail-title"
        aria-modal="true"
        className="admin-notifications-modal"
        role="dialog"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="admin-notifications-modal__header">
          <div className="admin-notifications-modal__title">
            <span className="admin-notifications-modal__icon">
              <FileText aria-hidden="true" />
            </span>
            <div>
              <h2 id="admin-notification-detail-title">
                {sourceLabel && (
                  <span className="admin-notifications-modal__source">
                    [{sourceLabel.toUpperCase()}]
                  </span>
                )}
                {title}
              </h2>
            </div>
          </div>
          <div className="admin-notifications-modal__actions">
            <button aria-label="Close notification detail" type="button" onClick={onClose}>
              <X aria-hidden="true" />
            </button>
          </div>
        </header>

        <div className="admin-notifications-modal__body pl-scrollbar pl-scrollbar--stable">
          {detailError && (
            <p className="admin-notifications-alert" role="alert">
              {detailError}
            </p>
          )}
          <AdminNotificationDetail
            loadState={loadState}
            notification={notification}
            recipient={recipient}
          />
        </div>
      </section>
    </div>
  )
}

function AdminNotificationsPageContent({ routeNotificationId }) {
  const { currentUser } = useAuth()
  const navigate = useNavigate()
  const [detailError, setDetailError] = useState('')
  const [detailLoadState, setDetailLoadState] = useState('idle')
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [listError, setListError] = useState('')
  const [listLoadState, setListLoadState] = useState('idle')
  const [nextCursor, setNextCursor] = useState('')
  const [notifications, setNotifications] = useState([])
  const [recipientQuery, setRecipientQuery] = useState('')
  const [recipientOptions, setRecipientOptions] = useState([])
  const [recipientSearchState, setRecipientSearchState] = useState('idle')
  const [selectedRecipient, setSelectedRecipient] = useState(null)
  const [selectedNotification, setSelectedNotification] = useState(null)
  const [selectedNotificationId, setSelectedNotificationId] = useState(
    routeNotificationId || null,
  )
  const [selectedRecipientId, setSelectedRecipientId] = useState('')
  const collectionRequestRef = useRef({ controller: null, id: 0 })
  const detailRequestRef = useRef({ controller: null, id: 0 })
  const recipientSearchRequestRef = useRef({ controller: null, id: 0 })

  useEffect(() => (
    () => {
      collectionRequestRef.current.controller?.abort()
      detailRequestRef.current.controller?.abort()
      recipientSearchRequestRef.current.controller?.abort()
    }
  ), [])

  useEffect(() => {
    const { controller, requestId } = beginAdminNotificationRequest(detailRequestRef)

    async function loadSelectedNotification() {
      if (!currentUser || !selectedNotificationId) {
        setSelectedNotification(null)
        setDetailError('')
        setDetailLoadState('idle')
        return
      }

      setDetailLoadState('loading')
      setDetailError('')
      setSelectedNotification(null)

      try {
        const nextNotification = await getAdminNotification({
          firebaseUser: currentUser,
          notificationId: selectedNotificationId,
          signal: controller.signal,
        })

        if (!shouldApplyAdminNotificationResponse({
          activeRequestId: detailRequestRef.current.id,
          requestId,
          signal: controller.signal,
        })) {
          return
        }

        setSelectedNotification(nextNotification)
        setDetailLoadState('ready')
      } catch (error) {
        if (
          isAbortError(error)
          || !shouldApplyAdminNotificationResponse({
            activeRequestId: detailRequestRef.current.id,
            requestId,
            signal: controller.signal,
          })
        ) {
          return
        }

        setSelectedNotification(null)
        setDetailError(error.message || 'Notification detail could not be loaded.')
        setDetailLoadState('error')
      }
    }

    loadSelectedNotification()

    return () => {
      controller.abort()
    }
  }, [currentUser, selectedNotificationId])

  useEffect(() => {
    const normalizedQuery = recipientQuery.trim()
    if (!currentUser || selectedRecipient || normalizedQuery.length < USER_SEARCH_MIN_LENGTH) {
      return undefined
    }

    const { controller, requestId } = beginAdminNotificationRequest(
      recipientSearchRequestRef,
    )
    const timeoutId = window.setTimeout(() => {
      setRecipientSearchState('loading')
      listAdminLookupUsers({
        firebaseUser: currentUser,
        limit: USER_SEARCH_LIMIT,
        query: normalizedQuery,
        signal: controller.signal,
      })
        .then((users) => {
          if (!shouldApplyAdminNotificationResponse({
            activeRequestId: recipientSearchRequestRef.current.id,
            requestId,
            signal: controller.signal,
          })) {
            return
          }
          setRecipientOptions(users)
          setRecipientSearchState('ready')
        })
        .catch((error) => {
          if (
            isAbortError(error)
            || !shouldApplyAdminNotificationResponse({
              activeRequestId: recipientSearchRequestRef.current.id,
              requestId,
              signal: controller.signal,
            })
          ) {
            return
          }
          setRecipientOptions([])
          setRecipientSearchState('error')
        })
    }, USER_SEARCH_DEBOUNCE_MS)

    return () => {
      controller.abort()
      window.clearTimeout(timeoutId)
    }
  }, [currentUser, recipientQuery, selectedRecipient])

  function abortCollectionRequest() {
    cancelAdminNotificationRequest(collectionRequestRef)
  }

  function abortDetailRequest() {
    cancelAdminNotificationRequest(detailRequestRef)
  }

  function abortRecipientSearchRequest() {
    cancelAdminNotificationRequest(recipientSearchRequestRef)
  }

  function applyClearedDetailState(clearedState) {
    setDetailError(clearedState.detailError)
    setDetailLoadState(clearedState.detailLoadState)
    setSelectedNotification(clearedState.selectedNotification)
    setSelectedNotificationId(clearedState.selectedNotificationId)
  }

  function clearCollectionState() {
    abortCollectionRequest()
    abortDetailRequest()
    const clearedState = buildAdminNotificationClearedCollectionState()
    setIsLoadingMore(false)
    setListError(clearedState.listError)
    setListLoadState(clearedState.listLoadState)
    setNextCursor(clearedState.nextCursor)
    setNotifications(clearedState.notifications)
    applyClearedDetailState(clearedState)
  }

  function collectionFilters(recipientId = selectedRecipientId) {
    return buildAdminNotificationCollectionFilters({
      selectedRecipientId: recipientId,
    })
  }

  async function loadCollection({
    append = false,
    nextLookupCursor = '',
    recipientId = selectedRecipientId,
  } = {}) {
    if (!currentUser || !recipientId) {
      return
    }

    const { controller, requestId } = beginAdminNotificationRequest(collectionRequestRef)
    const isAppend = append && Boolean(nextLookupCursor)

    if (isAppend) {
      setIsLoadingMore(true)
    } else {
      abortDetailRequest()
      setNotifications([])
      setIsLoadingMore(false)
      setListLoadState('loading')
      setSelectedNotification(null)
      setSelectedNotificationId(null)
      setDetailError('')
      setDetailLoadState('idle')
    }
    setListError('')

    try {
      const response = await listAdminNotifications({
        cursor: nextLookupCursor,
        firebaseUser: currentUser,
        filters: collectionFilters(recipientId),
        signal: controller.signal,
      })

      if (!shouldApplyAdminNotificationResponse({
        activeRequestId: collectionRequestRef.current.id,
        requestId,
        signal: controller.signal,
      })) {
        return
      }

      const nextNotifications = response.notifications ?? []
      setNotifications((currentNotifications) => (
        isAppend
          ? [...currentNotifications, ...nextNotifications]
          : nextNotifications
      ))
      setNextCursor(response.next_cursor || '')
      setIsLoadingMore(false)
      setListLoadState('ready')
    } catch (error) {
      if (
        isAbortError(error)
        || !shouldApplyAdminNotificationResponse({
          activeRequestId: collectionRequestRef.current.id,
          requestId,
          signal: controller.signal,
        })
      ) {
        return
      }

      if (!isAppend) {
        setNotifications([])
        setNextCursor('')
        setSelectedNotificationId(null)
      }
      setIsLoadingMore(false)
      setListError(error.message || 'Notification lookup could not be loaded.')
      setListLoadState(isAppend ? 'ready' : 'error')
    }
  }

  function handleRecipientQueryChange(value) {
    abortRecipientSearchRequest()
    setRecipientQuery(value)
    setRecipientOptions([])
    setRecipientSearchState('idle')
    setSelectedRecipient(null)
    setSelectedRecipientId('')
    clearCollectionState()
  }

  function handleSelectedRecipientChange(user) {
    setSelectedRecipient(user)
    setSelectedRecipientId(user.id)
    setRecipientQuery(recipientDisplayName(user))
    setRecipientOptions([])
    setRecipientSearchState('idle')
    clearCollectionState()
    loadCollection({
      nextLookupCursor: '',
      recipientId: user.id,
    })
  }

  function handleClearRecipient() {
    abortRecipientSearchRequest()
    setRecipientQuery('')
    setRecipientOptions([])
    setRecipientSearchState('idle')
    setSelectedRecipient(null)
    setSelectedRecipientId('')
    clearCollectionState()
  }

  function handleLoadMore() {
    if (!nextCursor || isLoadingMore) {
      return
    }

    loadCollection({
      append: true,
      nextLookupCursor: nextCursor,
    })
  }

  function handleCloseDetailModal() {
    abortDetailRequest()
    setDetailError('')
    setDetailLoadState('idle')
    setSelectedNotification(null)
    setSelectedNotificationId(null)

    if (routeNotificationId) {
      navigate('/admin/notifications', { replace: true })
    }
  }

  const shouldShowResultsPanel = (
    listLoadState === 'loading'
    || listLoadState === 'ready'
  )
  const shouldShowDetailModal = Boolean(
    selectedNotificationId
    || selectedNotification
    || detailLoadState === 'loading'
    || detailLoadState === 'error',
  )
  const shouldShowRecipientMenu = (
    !selectedRecipient
    && recipientQuery.trim().length >= USER_SEARCH_MIN_LENGTH
    && (
      recipientSearchState === 'loading'
      || recipientSearchState === 'error'
      || recipientSearchState === 'ready'
    )
  )
  return (
    <AdminWorkspaceLayout
      breadcrumbs={['Admin', 'System', 'Notification Lookup']}
      description="Find generated user notifications. Platform Notices are managed separately."
      icon={Bell}
      title="Notification Lookup"
    >
      <div className="admin-notifications-layout">
        <section
          aria-label="Notification lookup"
          className="admin-notifications-panel admin-notifications-lookup-panel"
        >
          <div className="admin-notifications-panel__heading">
            <div>
              <ShieldCheck />
              <h2>Find Notifications</h2>
            </div>
          </div>

          <div className="admin-notifications-filters">
            <div className="admin-notifications-user-search">
              <span>Recipient</span>
              <div className="admin-notifications-user-search__field">
                {selectedRecipient ? (
                  <AdminNotificationRecipientToken
                    user={selectedRecipient}
                    onClear={handleClearRecipient}
                  />
                ) : (
                  <>
                    <input
                      autoComplete="off"
                      placeholder="Search by name, email, or user ID"
                      value={recipientQuery}
                      onChange={(event) => handleRecipientQueryChange(event.target.value)}
                    />
                    {shouldShowRecipientMenu && (
                      <div className="admin-notifications-user-search__menu">
                        {recipientSearchState === 'loading' && <p>Searching...</p>}
                        {recipientSearchState === 'error' && (
                          <p role="alert">User lookup failed.</p>
                        )}
                        {recipientSearchState === 'ready' && recipientOptions.length === 0 && (
                          <p>No matching users found.</p>
                        )}
                        {recipientSearchState === 'ready' && recipientOptions.map((user) => (
                          <button
                            key={user.id}
                            type="button"
                            onClick={() => handleSelectedRecipientChange(user)}
                          >
                            <span>
                              <strong>{recipientDisplayName(user)}</strong>
                              <small>{user.email || user.id}</small>
                            </span>
                          </button>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>

          {listError && (
            <p className="admin-notifications-alert" role="alert">
              {listError}
            </p>
          )}

        </section>

        {shouldShowResultsPanel && (
          <section
            aria-label="Notification results"
            className="admin-notifications-panel admin-notifications-results-panel"
          >
            <div className="admin-notifications-panel__heading">
              <div>
                <Search />
                <h2>Notification History</h2>
              </div>
            </div>

            {listLoadState === 'loading' && (
              <AdminNotificationsLoading />
            )}
            {listLoadState === 'ready' && notifications.length === 0 && (
              <div className="admin-notifications-empty-state">
                <Bell aria-hidden="true" />
                <strong>No notifications found</strong>
                <span>This user has no generated notifications.</span>
              </div>
            )}
            {listLoadState === 'ready' && notifications.length > 0 && (
              <>
                <div className="admin-notifications-list">
                  {notifications.map((notification) => (
                    <AdminNotificationRow
                      key={notification.id}
                      notification={notification}
                      onSelect={setSelectedNotificationId}
                    />
                  ))}
                </div>

                {nextCursor && (
                  <div className="admin-notifications-load-more">
                    <button
                      className="admin-notifications-button"
                      disabled={isLoadingMore}
                      type="button"
                      onClick={handleLoadMore}
                    >
                      {isLoadingMore ? 'Loading...' : 'Load more'}
                    </button>
                  </div>
                )}
              </>
            )}
          </section>
        )}
      </div>
      {shouldShowDetailModal && (
        <AdminNotificationDetailModal
          detailError={detailError}
          loadState={detailLoadState}
          notification={selectedNotification}
          recipient={selectedRecipient}
          onClose={handleCloseDetailModal}
        />
      )}
    </AdminWorkspaceLayout>
  )
}

function AdminNotificationsPage() {
  const { notificationId: routeNotificationId = '' } = useParams()

  return (
    <AdminNotificationsPageContent
      key={routeNotificationId || 'notification-lookup'}
      routeNotificationId={routeNotificationId}
    />
  )
}

export default AdminNotificationsPage
