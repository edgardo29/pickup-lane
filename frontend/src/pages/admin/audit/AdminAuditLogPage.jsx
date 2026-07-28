import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ExternalLink,
  FileClock,
  FileText,
  Search,
  ShieldCheck,
  X,
} from 'lucide-react'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminAuditLog.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import {
  getAdminAction,
  listAdminActionLog,
  listAdminLookupUsers,
} from '../shared/adminApi.js'
import { selectAdminActionPrimaryTarget } from './adminAuditLogTargets.js'

const ADMIN_SEARCH_DEBOUNCE_MS = 300
const ADMIN_SEARCH_LIMIT = 10
const ADMIN_SEARCH_MIN_LENGTH = 3

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

function isAbortError(error) {
  return error?.name === 'AbortError'
}

function beginAdminActionRequest(requestRef) {
  requestRef.current.controller?.abort()
  const requestId = requestRef.current.id + 1
  const controller = new AbortController()
  requestRef.current = { controller, id: requestId }

  return { controller, requestId }
}

function cancelAdminActionRequest(requestRef) {
  requestRef.current.controller?.abort()
  requestRef.current = {
    controller: null,
    id: requestRef.current.id + 1,
  }
}

function shouldApplyAdminActionResponse({
  activeRequestId,
  requestId,
  signal,
} = {}) {
  return !signal?.aborted && activeRequestId === requestId
}

function adminDisplayName(user) {
  if (!user) {
    return ''
  }

  return user.display_name || user.email || user.id
}

function actionLabelForDetail(action, logAction, actionTypeOptions) {
  if (logAction?.action_label) {
    return logAction.action_label
  }

  return actionTypeOptions.find((option) => option.action_type === action?.action_type)?.label
    || action?.action_type
    || 'Admin action'
}

function AdminActionLogLoading() {
  return (
    <div
      aria-label="Loading admin actions"
      className="admin-audit-loading"
      role="status"
    >
      {Array.from({ length: 4 }).map((_, index) => (
        <div className="admin-audit-loading__row" key={index}>
          <SkeletonBlock height="0.95rem" rounded width="38%" />
          <SkeletonBlock height="0.78rem" rounded width="62%" />
          <SkeletonBlock height="0.72rem" rounded width="28%" />
        </div>
      ))}
    </div>
  )
}

function AdminActionLogAdminToken({ admin, onClear }) {
  return (
    <div className="admin-audit-admin-token">
      <div>
        <strong>{adminDisplayName(admin)}</strong>
        <span>{admin.email || admin.id}</span>
      </div>
      <button aria-label="Clear selected admin" type="button" onClick={onClear}>
        <X aria-hidden="true" />
      </button>
    </div>
  )
}

function AdminActionLogRow({ action, onSelect }) {
  return (
    <button
      className="admin-audit-row"
      type="button"
      onClick={() => onSelect(action)}
    >
      <span className="admin-audit-row__icon" aria-hidden="true">
        <FileText />
      </span>
      <span className="admin-audit-row__main">
        <strong>{action.action_label}</strong>
        <span>
          {action.admin_label}
          {' - '}
          {action.target_label}
        </span>
        {action.reason_preview && <small>{action.reason_preview}</small>}
      </span>
      <time dateTime={action.created_at}>{formatDateTime(action.created_at)}</time>
    </button>
  )
}

function AdminActionDetailField({
  label,
  value,
}) {
  return (
    <div className="admin-audit-detail-fact">
      <span>{label}</span>
      <strong>{value || 'None'}</strong>
    </div>
  )
}

function AdminActionTargets({ action, logAction }) {
  const targets = Array.isArray(action?.target_details) ? action.target_details : []
  const primaryTarget = selectAdminActionPrimaryTarget({
    detailTargets: targets,
    listPrimaryTarget: logAction?.primary_target,
  })

  if (!primaryTarget) {
    return null
  }

  return (
    <section className="admin-audit-detail-section">
      <h3>Target</h3>
      <div className="admin-audit-target-summary">
        <div>
          <span>{primaryTarget.target_type_label}</span>
          <strong>{primaryTarget.label}</strong>
        </div>
        {primaryTarget.destination_path && (
          <Link to={primaryTarget.destination_path}>
            <ExternalLink aria-hidden="true" />
            Open admin page
          </Link>
        )}
      </div>
    </section>
  )
}

function AdminActionDetail({
  action,
  loadState,
  logAction,
}) {
  if (loadState === 'loading') {
    return <p className="admin-audit-empty">Loading action detail.</p>
  }

  if (loadState === 'error' && !action) {
    return null
  }

  if (!action) {
    return null
  }

  const adminLabel = (
    logAction?.admin_label
    || action.admin_user_display_name
    || action.admin_user_email
    || action.admin_user_id
  )

  return (
    <div className="admin-audit-detail">
      <section className="admin-audit-detail-section">
        <h3>Action</h3>
        <div className="admin-audit-detail-facts">
          <AdminActionDetailField label="Admin" value={adminLabel} />
          {action.admin_user_email && (
            <AdminActionDetailField label="Admin email" value={action.admin_user_email} />
          )}
          <AdminActionDetailField
            label="Created"
            value={formatDateTime(action.created_at)}
          />
          {action.reason && (
            <AdminActionDetailField label="Reason" value={action.reason} />
          )}
        </div>
      </section>

      <AdminActionTargets action={action} logAction={logAction} />
    </div>
  )
}

function AdminActionDetailModal({
  action,
  actionTypeOptions,
  detailError,
  loadState,
  logAction,
  onClose,
}) {
  const title = actionLabelForDetail(action, logAction, actionTypeOptions)

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
      className="admin-audit-modal-backdrop"
      role="presentation"
      onClick={onClose}
    >
      <section
        aria-labelledby="admin-action-detail-title"
        aria-modal="true"
        className="admin-audit-modal"
        role="dialog"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="admin-audit-modal__header">
          <div className="admin-audit-modal__title">
            <span className="admin-audit-modal__icon">
              <FileClock aria-hidden="true" />
            </span>
            <h2 id="admin-action-detail-title">{title}</h2>
          </div>
          <button aria-label="Close action detail" type="button" onClick={onClose}>
            <X aria-hidden="true" />
          </button>
        </header>

        <div className="admin-audit-modal__body pl-scrollbar pl-scrollbar--stable">
          {detailError && (
            <p className="admin-audit-alert" role="alert">
              {detailError}
            </p>
          )}
          <AdminActionDetail
            action={action}
            loadState={loadState}
            logAction={logAction}
          />
        </div>
      </section>
    </div>
  )
}

function AdminAuditLogPage() {
  const { currentUser } = useAuth()
  const [actionTypeFilter, setActionTypeFilter] = useState('')
  const [actionTypeOptions, setActionTypeOptions] = useState([])
  const [actions, setActions] = useState([])
  const [adminOptions, setAdminOptions] = useState([])
  const [adminQuery, setAdminQuery] = useState('')
  const [adminSearchState, setAdminSearchState] = useState('idle')
  const [detailError, setDetailError] = useState('')
  const [detailLoadState, setDetailLoadState] = useState('idle')
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [listError, setListError] = useState('')
  const [listLoadState, setListLoadState] = useState('loading')
  const [nextCursor, setNextCursor] = useState('')
  const [selectedAction, setSelectedAction] = useState(null)
  const [selectedActionId, setSelectedActionId] = useState(null)
  const [selectedAdmin, setSelectedAdmin] = useState(null)
  const [selectedAdminId, setSelectedAdminId] = useState('')
  const [selectedLogAction, setSelectedLogAction] = useState(null)
  const adminSearchRequestRef = useRef({ controller: null, id: 0 })
  const collectionRequestRef = useRef({ controller: null, id: 0 })
  const detailRequestRef = useRef({ controller: null, id: 0 })

  useEffect(() => (
    () => {
      adminSearchRequestRef.current.controller?.abort()
      collectionRequestRef.current.controller?.abort()
      detailRequestRef.current.controller?.abort()
    }
  ), [])

  useEffect(() => {
    const normalizedQuery = adminQuery.trim()
    if (!currentUser || selectedAdmin || normalizedQuery.length < ADMIN_SEARCH_MIN_LENGTH) {
      return undefined
    }

    const { controller, requestId } = beginAdminActionRequest(adminSearchRequestRef)
    const timeoutId = window.setTimeout(() => {
      setAdminSearchState('loading')
      listAdminLookupUsers({
        accountStatus: 'active',
        firebaseUser: currentUser,
        limit: ADMIN_SEARCH_LIMIT,
        query: normalizedQuery,
        role: 'admin',
        signal: controller.signal,
      })
        .then((users) => {
          if (!shouldApplyAdminActionResponse({
            activeRequestId: adminSearchRequestRef.current.id,
            requestId,
            signal: controller.signal,
          })) {
            return
          }
          setAdminOptions(users)
          setAdminSearchState('ready')
        })
        .catch((error) => {
          if (
            isAbortError(error)
            || !shouldApplyAdminActionResponse({
              activeRequestId: adminSearchRequestRef.current.id,
              requestId,
              signal: controller.signal,
            })
          ) {
            return
          }
          setAdminOptions([])
          setAdminSearchState('error')
        })
    }, ADMIN_SEARCH_DEBOUNCE_MS)

    return () => {
      controller.abort()
      window.clearTimeout(timeoutId)
    }
  }, [adminQuery, currentUser, selectedAdmin])

  useEffect(() => {
    const { controller, requestId } = beginAdminActionRequest(collectionRequestRef)

    async function loadActions() {
      if (!currentUser) {
        return
      }

      detailRequestRef.current.controller?.abort()
      setActions([])
      setDetailError('')
      setDetailLoadState('idle')
      setIsLoadingMore(false)
      setListError('')
      setListLoadState('loading')
      setNextCursor('')
      setSelectedAction(null)
      setSelectedActionId(null)
      setSelectedLogAction(null)

      try {
        const response = await listAdminActionLog({
          firebaseUser: currentUser,
          filters: {
            admin_user_id: selectedAdminId,
            action_type: actionTypeFilter,
          },
          signal: controller.signal,
        })

        if (!shouldApplyAdminActionResponse({
          activeRequestId: collectionRequestRef.current.id,
          requestId,
          signal: controller.signal,
        })) {
          return
        }

        setActions(response.actions ?? [])
        setActionTypeOptions(response.action_type_options ?? [])
        setNextCursor(response.next_cursor || '')
        setListLoadState('ready')
      } catch (error) {
        if (
          isAbortError(error)
          || !shouldApplyAdminActionResponse({
            activeRequestId: collectionRequestRef.current.id,
            requestId,
            signal: controller.signal,
          })
        ) {
          return
        }

        setActions([])
        setNextCursor('')
        setListError(error.message || 'Admin Action Log could not be loaded.')
        setListLoadState('error')
      }
    }

    loadActions()

    return () => {
      controller.abort()
    }
  }, [actionTypeFilter, currentUser, selectedAdminId])

  useEffect(() => {
    const { controller, requestId } = beginAdminActionRequest(detailRequestRef)

    async function loadSelectedAction() {
      if (!currentUser || !selectedActionId) {
        setSelectedAction(null)
        setDetailError('')
        setDetailLoadState('idle')
        return
      }

      setDetailError('')
      setDetailLoadState('loading')
      setSelectedAction(null)

      try {
        const nextAction = await getAdminAction({
          adminActionId: selectedActionId,
          firebaseUser: currentUser,
          signal: controller.signal,
        })

        if (!shouldApplyAdminActionResponse({
          activeRequestId: detailRequestRef.current.id,
          requestId,
          signal: controller.signal,
        })) {
          return
        }

        setSelectedAction(nextAction)
        setDetailLoadState('ready')
      } catch (error) {
        if (
          isAbortError(error)
          || !shouldApplyAdminActionResponse({
            activeRequestId: detailRequestRef.current.id,
            requestId,
            signal: controller.signal,
          })
        ) {
          return
        }

        setSelectedAction(null)
        setDetailError(error.message || 'Admin action detail could not be loaded.')
        setDetailLoadState('error')
      }
    }

    loadSelectedAction()

    return () => {
      controller.abort()
    }
  }, [currentUser, selectedActionId])

  async function loadMoreActions() {
    if (!currentUser || !nextCursor || isLoadingMore) {
      return
    }

    const { controller, requestId } = beginAdminActionRequest(collectionRequestRef)
    setIsLoadingMore(true)
    setListError('')

    try {
      const response = await listAdminActionLog({
        cursor: nextCursor,
        firebaseUser: currentUser,
        filters: {
          admin_user_id: selectedAdminId,
          action_type: actionTypeFilter,
        },
        signal: controller.signal,
      })

      if (!shouldApplyAdminActionResponse({
        activeRequestId: collectionRequestRef.current.id,
        requestId,
        signal: controller.signal,
      })) {
        return
      }

      setActions((currentActions) => [
        ...currentActions,
        ...(response.actions ?? []),
      ])
      setActionTypeOptions(response.action_type_options ?? actionTypeOptions)
      setNextCursor(response.next_cursor || '')
      setIsLoadingMore(false)
      setListLoadState('ready')
    } catch (error) {
      if (
        isAbortError(error)
        || !shouldApplyAdminActionResponse({
          activeRequestId: collectionRequestRef.current.id,
          requestId,
          signal: controller.signal,
        })
      ) {
        return
      }

      setIsLoadingMore(false)
      setListError(error.message || 'More admin actions could not be loaded.')
    }
  }

  function handleAdminQueryChange(value) {
    cancelAdminActionRequest(adminSearchRequestRef)
    setAdminQuery(value)
    setAdminOptions([])
    setAdminSearchState('idle')
    setSelectedAdmin(null)
    setSelectedAdminId('')
  }

  function handleSelectedAdminChange(admin) {
    setSelectedAdmin(admin)
    setSelectedAdminId(admin.id)
    setAdminQuery(adminDisplayName(admin))
    setAdminOptions([])
    setAdminSearchState('idle')
  }

  function handleClearAdmin() {
    cancelAdminActionRequest(adminSearchRequestRef)
    setAdminQuery('')
    setAdminOptions([])
    setAdminSearchState('idle')
    setSelectedAdmin(null)
    setSelectedAdminId('')
  }

  function handleSelectAction(action) {
    setSelectedLogAction(action)
    setSelectedActionId(action.id)
  }

  function handleCloseDetailModal() {
    cancelAdminActionRequest(detailRequestRef)
    setDetailError('')
    setDetailLoadState('idle')
    setSelectedAction(null)
    setSelectedActionId(null)
    setSelectedLogAction(null)
  }

  const shouldShowAdminMenu = (
    !selectedAdmin
    && adminQuery.trim().length >= ADMIN_SEARCH_MIN_LENGTH
    && ['loading', 'error', 'ready'].includes(adminSearchState)
  )
  const shouldShowDetailModal = Boolean(
    selectedActionId
    || selectedLogAction
    || selectedAction
    || detailLoadState === 'loading'
    || detailLoadState === 'error',
  )

  return (
    <AdminWorkspaceLayout
      breadcrumbs={['Admin', 'System', 'Admin Action Log']}
      description="Review successful staff actions across Pickup Lane."
      icon={FileClock}
      title="Admin Action Log"
    >
      <div className="admin-audit-layout">
        <section className="admin-audit-panel" aria-label="Recent admin actions">
          <div className="admin-audit-panel__heading">
            <div>
              <ShieldCheck />
              <h2>Recent admin actions</h2>
            </div>
          </div>

          <div className="admin-audit-filters">
            <div className="admin-audit-admin-search">
              <span>Admin</span>
              <div className="admin-audit-admin-search__field">
                {selectedAdmin ? (
                  <AdminActionLogAdminToken
                    admin={selectedAdmin}
                    onClear={handleClearAdmin}
                  />
                ) : (
                  <>
                    <input
                      autoComplete="off"
                      placeholder="Search staff by name or email"
                      value={adminQuery}
                      onChange={(event) => handleAdminQueryChange(event.target.value)}
                    />
                    {shouldShowAdminMenu && (
                      <div className="admin-audit-admin-search__menu">
                        {adminSearchState === 'loading' && <p>Searching...</p>}
                        {adminSearchState === 'error' && (
                          <p role="alert">Admin lookup failed.</p>
                        )}
                        {adminSearchState === 'ready' && adminOptions.length === 0 && (
                          <p>No matching admins found.</p>
                        )}
                        {adminSearchState === 'ready' && adminOptions.map((admin) => (
                          <button
                            key={admin.id}
                            type="button"
                            onClick={() => handleSelectedAdminChange(admin)}
                          >
                            <span>
                              <strong>{adminDisplayName(admin)}</strong>
                              <small>{admin.email || admin.id}</small>
                            </span>
                          </button>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>

            <label className="admin-audit-action-filter">
              <span>Action type</span>
              <select
                value={actionTypeFilter}
                onChange={(event) => setActionTypeFilter(event.target.value)}
              >
                <option value="">All actions</option>
                {actionTypeOptions.map((option) => (
                  <option key={option.action_type} value={option.action_type}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {listError && (
            <p className="admin-audit-alert" role="alert">
              {listError}
            </p>
          )}

          {listLoadState === 'loading' && <AdminActionLogLoading />}

          {listLoadState === 'ready' && actions.length === 0 && (
            <div className="admin-audit-empty-state">
              <Search aria-hidden="true" />
              <strong>No admin actions found</strong>
              <span>No matching successful admin actions were found.</span>
            </div>
          )}

          {listLoadState === 'ready' && actions.length > 0 && (
            <>
              <div className="admin-audit-list">
                {actions.map((action) => (
                  <AdminActionLogRow
                    action={action}
                    key={action.id}
                    onSelect={handleSelectAction}
                  />
                ))}
              </div>

              {nextCursor && (
                <div className="admin-audit-load-more">
                  <button
                    className="admin-audit-button"
                    disabled={isLoadingMore}
                    type="button"
                    onClick={loadMoreActions}
                  >
                    {isLoadingMore ? 'Loading...' : 'Load more'}
                  </button>
                </div>
              )}
            </>
          )}
        </section>
      </div>

      {shouldShowDetailModal && (
        <AdminActionDetailModal
          action={selectedAction}
          actionTypeOptions={actionTypeOptions}
          detailError={detailError}
          loadState={detailLoadState}
          logAction={selectedLogAction}
          onClose={handleCloseDetailModal}
        />
      )}
    </AdminWorkspaceLayout>
  )
}

export default AdminAuditLogPage
