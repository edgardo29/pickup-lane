import { useCallback, useEffect, useRef, useState } from 'react'
import { Image as ImageIcon } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeftIcon,
  ChatIcon,
  ClipboardListIcon,
  DollarIcon,
  PencilIcon,
  ShieldCheckIcon,
  TrashIcon,
  UsersIcon,
} from '../../../../components/BrowseIcons.jsx'
import { useAuth } from '../../../../hooks/useAuth.js'
import { buildMediaUrl } from '../../../../lib/apiClient.js'
import '../../../../styles/admin/AdminOfficialGames.css'
import AdminWorkspaceLayout from '../../shared/AdminWorkspaceLayout.jsx'
import {
  ADMIN_PERMISSIONS,
  hasAnyAdminPermission,
  hasAdminPermission,
} from '../../shared/adminWorkspaceData.js'
import { listAdminActions } from '../../shared/adminApi.js'
import { useAdminAccess } from '../../shared/useAdminAccess.js'
import AdminOfficialGameAuditTab from './AdminOfficialGameAuditTab.jsx'
import AdminOfficialGameBookingsTab from './AdminOfficialGameBookingsTab.jsx'
import AdminOfficialGameChatTab from './AdminOfficialGameChatTab.jsx'
import AdminOfficialGameHostPanel from './AdminOfficialGameHostPanel.jsx'
import AdminOfficialGameMoneyTab from './AdminOfficialGameMoneyTab.jsx'
import AdminOfficialGameRemovalPreviewModal from './AdminOfficialGameRemovalPreviewModal.jsx'
import AdminOfficialGameRosterPanel from './AdminOfficialGameRosterPanel.jsx'
import AdminOfficialGameSummary from './AdminOfficialGameSummary.jsx'
import AdminOfficialGameWaitlistTab from './AdminOfficialGameWaitlistTab.jsx'
import { getPrimaryGameChat } from './adminOfficialGameManageDisplay.js'
import { useAdminOfficialGameLedgers } from './useAdminOfficialGameLedgers.js'
import {
  addAdminOfficialGamePlayer,
  assignAdminOfficialGameHost,
  cancelAdminOfficialGame,
  executeAdminOfficialGamePlayerRemoval,
  getAdminOfficialGame,
  listAdminOfficialGameChatMessages,
  listAdminOfficialGameChatRooms,
  listOfficialGameVenueImages,
  listAdminOfficialGameParticipants,
  previewAdminOfficialGameCancellation,
  previewAdminOfficialGamePlayerRemoval,
  removeAdminOfficialGameHost,
  removeAdminOfficialGamePlayer,
  searchAdminOfficialGameUsers,
} from '../shared/adminOfficialGamesApi.js'
import {
  formatAdminGameMoney,
} from '../shared/adminOfficialGameForm.js'

const manageTabs = [
  { id: 'roster', label: 'Roster' },
  { id: 'bookings', label: 'Bookings' },
  { id: 'waitlist', label: 'Waitlist' },
  { id: 'money', label: 'Money' },
  { id: 'chat', label: 'Chat' },
  { id: 'photos', label: 'Photos' },
  { id: 'audit', label: 'Activity' },
]

const cancellableGameStatuses = new Set(['scheduled', 'full'])

function getCancelDisabledReason(game) {
  if (!game) {
    return ''
  }

  if (game.game_status === 'cancelled') {
    return 'Game already cancelled.'
  }

  if (!cancellableGameStatuses.has(game.game_status)) {
    return 'Only scheduled or full games can be cancelled.'
  }

  if (new Date(game.starts_at).getTime() <= Date.now()) {
    return 'Games cannot be cancelled after start time.'
  }

  return ''
}

const cancellationCategoryLabels = {
  cancel_only: 'Cancel only',
  credit_restore: 'Restore credit',
  credit_restored: 'Credit restored',
  follow_up_required: 'Follow-up required',
  pending_hold_release: 'Release pending hold',
  pending_hold_released: 'Pending hold released',
  stripe_refund: 'Refund cash',
  stripe_refund_and_credit_restore: 'Refund cash + restore credit',
  stripe_refunded: 'Cash refunded',
  stripe_refunded_and_credit_restored: 'Cash refunded + credit restored',
}

const cancellationFollowUpLabels = {
  active_refund: 'Active refund',
  existing_or_disputed_refund_state: 'Existing refund or dispute state',
  missing_stripe_charge_id: 'Missing Stripe charge',
  payment_state_follow_up: 'Payment state follow-up',
  processing_payment: 'Processing payment',
  stripe_refund_failed: 'Stripe refund failed',
  stripe_refund_processing: 'Stripe refund processing',
}

function getCancellationCategoryLabel(category) {
  return cancellationCategoryLabels[category] || category || 'Review'
}

function getCancellationFollowUpLabel(reason) {
  return cancellationFollowUpLabels[reason] || reason || ''
}

function getCancellationCreditCents(row) {
  const restoredCents = row.credit_restored_cents ?? row.credit_restorable_cents ?? 0
  const releasedCents = row.credit_released_cents ?? row.credit_releasable_cents ?? 0
  return restoredCents + releasedCents
}

function AdminOfficialGameCancelModal({
  cancelReason,
  error,
  game,
  isLoadingPreview,
  isCancelling,
  onCancelReasonChange,
  onClose,
  onConfirm,
  onCreateReplacement,
  preview,
  result,
}) {
  const bookingRows = result?.booking_results || preview?.booking_impacts || []
  const canConfirm = Boolean(preview?.preview_token && cancelReason.trim()) && !isCancelling
  const summary = result || preview

  return (
    <div className="admin-official-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="admin-official-confirm-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-cancel-official-game-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="admin-official-confirm-modal__copy">
          <h2 id="admin-cancel-official-game-title">
            {result ? 'Official game cancelled' : 'Cancel official game?'}
          </h2>
          <p>
            {result
              ? `${game.title} was cancelled. Review any follow-up rows before leaving.`
              : `${game.title} will be cancelled for everyone. Money outcomes are based on the backend impact preview below.`}
          </p>
        </div>

        {error && <p className="admin-official-alert">{error}</p>}
        {isLoadingPreview && (
          <p className="admin-official-empty">Loading cancellation impact.</p>
        )}

        {summary && (
          <div className="admin-official-cancel-summary">
            <div>
              <span>Bookings</span>
              <strong>{result?.cancelled_booking_count ?? preview.booking_count}</strong>
            </div>
            <div>
              <span>Roster rows</span>
              <strong>{result?.cancelled_participant_count ?? preview.participant_count}</strong>
            </div>
            <div>
              <span>Waitlist rows</span>
              <strong>{result?.cancelled_waitlist_entry_count ?? preview.waitlist_entry_count}</strong>
            </div>
            <div>
              <span>Cash</span>
              <strong>
                {formatAdminGameMoney(
                  result
                    ? result.booking_results.reduce((total, row) => total + row.cash_refunded_cents, 0)
                    : preview.cash_refundable_cents,
                  game.currency,
                )}
              </strong>
            </div>
            <div>
              <span>Credit restore</span>
              <strong>
                {formatAdminGameMoney(
                  result?.credit_restored_cents ?? preview.credit_restorable_cents,
                  game.currency,
                )}
              </strong>
            </div>
            <div>
              <span>Credit release</span>
              <strong>
                {formatAdminGameMoney(
                  result?.credit_released_cents ?? preview.credit_releasable_cents,
                  game.currency,
                )}
              </strong>
            </div>
          </div>
        )}

        {bookingRows.length > 0 && (
          <div className="admin-official-cancel-rows" aria-label="Cancellation booking impact">
            {bookingRows.map((row) => (
              <div key={row.booking_id} className="admin-official-cancel-row">
                <div>
                  <strong>{getCancellationCategoryLabel(row.result_category)}</strong>
                  <span>{row.booking_payment_status}</span>
                </div>
                <div>
                  <span>Cash</span>
                  <strong>
                    {formatAdminGameMoney(
                      row.cash_refunded_cents ?? row.cash_refundable_cents ?? 0,
                      game.currency,
                    )}
                  </strong>
                </div>
                <div>
                  <span>Credit</span>
                  <strong>
                    {formatAdminGameMoney(
                      getCancellationCreditCents(row),
                      game.currency,
                    )}
                  </strong>
                </div>
                {row.follow_up_required && (
                  <div className="admin-official-cancel-row__warning">
                    {getCancellationFollowUpLabel(row.follow_up_reason)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {!result && (
          <label className="admin-official-textarea-field">
            <span>Internal reason</span>
            <textarea
              maxLength={500}
              placeholder="Required cancellation reason"
              value={cancelReason}
              onChange={(event) => onCancelReasonChange(event.target.value)}
            />
            <small>{cancelReason.length}/500</small>
          </label>
        )}

        {result?.support_flag_ids?.length > 0 && (
          <p className="admin-official-warning">
            Support follow-up was created for unresolved money state.
          </p>
        )}

        <div className="admin-official-confirm-modal__actions">
          <button
            className="admin-official-button"
            disabled={isCancelling}
            type="button"
            onClick={onClose}
          >
            {result ? 'Close' : 'Keep game'}
          </button>
          {result && (
            <button
              className="admin-official-button admin-official-button--primary"
              type="button"
              onClick={onCreateReplacement}
            >
              Create replacement
            </button>
          )}
          {!result && (
            <button
              className="admin-official-button admin-official-button--danger-solid"
              disabled={!canConfirm}
              type="button"
              onClick={onConfirm}
            >
              {isCancelling ? 'Cancelling' : 'Cancel game'}
            </button>
          )}
        </div>
      </section>
    </div>
  )
}

function AdminOfficialGameLockedTab({ description, icon: Icon, label, title }) {
  return (
    <section className="admin-manage-tab-panel admin-bookings-panel" aria-label={label}>
      <div className="admin-manage-panel-heading admin-bookings-heading">
        <div className="admin-bookings-heading__copy">
          <span className="admin-bookings-heading__icon">
            <Icon />
          </span>
          <div>
            <h2>{title}</h2>
            <p>{description}</p>
          </div>
        </div>
      </div>
    </section>
  )
}

function AdminOfficialGamePhotosTab({ venueImages }) {
  const primaryImage = venueImages.find((image) => image.is_primary) || venueImages[0]
  const galleryImages = venueImages.filter((image) => image.id !== primaryImage?.id)

  return (
    <section className="admin-manage-tab-panel admin-bookings-panel" aria-label="Official game photos">
      <div className="admin-manage-panel-heading admin-bookings-heading">
        <div className="admin-bookings-heading__copy">
          <span className="admin-bookings-heading__icon">
            <ImageIcon />
          </span>
          <div>
            <h2>Photos</h2>
            <p>Review venue photos shown on game pages.</p>
          </div>
        </div>
      </div>

      <div className="admin-manage-photos">
        <article className="admin-manage-photo-card admin-manage-photo-card--primary">
          <h2>Primary</h2>
          {primaryImage ? (
            <img
              className="admin-manage-primary-photo"
              src={buildMediaUrl(primaryImage.image_url)}
              alt=""
            />
          ) : (
            <div className="admin-manage-photo-empty">
              No primary photo yet.
            </div>
          )}
        </article>

        <article className="admin-manage-photo-card admin-manage-photo-card--gallery">
          <h2>Gallery</h2>
          {galleryImages.length > 0 ? (
            <div className="admin-manage-gallery-grid">
              {galleryImages.map((image) => (
                <img key={image.id} src={buildMediaUrl(image.image_url)} alt="" />
              ))}
            </div>
          ) : (
            <div className="admin-manage-photo-empty">
              No gallery photos yet.
            </div>
          )}
        </article>
      </div>
    </section>
  )
}

function AdminOfficialGamePageContent({ gameId }) {
  const { currentUser } = useAuth()
  const {
    adminAccess,
    isLoading: isAdminAccessLoading,
  } = useAdminAccess()
  const navigate = useNavigate()
  const currentAdminDataContextKey = currentUser ? `${currentUser.uid}:${gameId}` : ''
  const [game, setGame] = useState(null)
  const [workspaceContextKey, setWorkspaceContextKey] = useState('')
  const [participants, setParticipants] = useState([])
  const [chatRooms, setChatRooms] = useState([])
  const [chatMessages, setChatMessages] = useState([])
  const [chatContextKey, setChatContextKey] = useState('')
  const [chatLoadState, setChatLoadState] = useState('loading')
  const [chatError, setChatError] = useState('')
  const [chatRefreshCount, setChatRefreshCount] = useState(0)
  const [auditActions, setAuditActions] = useState([])
  const [auditContextKey, setAuditContextKey] = useState('')
  const [auditLoadState, setAuditLoadState] = useState('loading')
  const [auditError, setAuditError] = useState('')
  const [auditRefreshCount, setAuditRefreshCount] = useState(0)
  const [venueImages, setVenueImages] = useState([])
  const [activeTab, setActiveTab] = useState('roster')
  const [loadState, setLoadState] = useState('loading')
  const [mutationState, setMutationState] = useState('idle')
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false)
  const [previewParticipant, setPreviewParticipant] = useState(null)
  const [removalPreview, setRemovalPreview] = useState(null)
  const [removalPreviewState, setRemovalPreviewState] = useState('idle')
  const [removalPreviewError, setRemovalPreviewError] = useState('')
  const [removalExecutionResult, setRemovalExecutionResult] = useState(null)
  const [removalExecutionState, setRemovalExecutionState] = useState('idle')
  const [removalExecutionError, setRemovalExecutionError] = useState('')
  const [cancelReason, setCancelReason] = useState('')
  const [cancelPreview, setCancelPreview] = useState(null)
  const [cancelPreviewState, setCancelPreviewState] = useState('idle')
  const [cancelError, setCancelError] = useState('')
  const [cancelResult, setCancelResult] = useState(null)
  const [pageError, setPageError] = useState('')
  const [pageNotice, setPageNotice] = useState('')
  const removalPreviewRequestIdRef = useRef(0)
  const cancelPreviewRequestIdRef = useRef(0)
  const canEditGame = hasAdminPermission(
    adminAccess,
    ADMIN_PERMISSIONS.OFFICIAL_GAMES_WRITE,
  )
  const canManageRoster = hasAdminPermission(
    adminAccess,
    ADMIN_PERMISSIONS.OFFICIAL_GAMES_ROSTER_MANAGE,
  )
  const canSearchRosterUsers = (
    canManageRoster
    && hasAdminPermission(adminAccess, ADMIN_PERMISSIONS.USERS_READ)
  )
  const canPreviewRemovals = (
    canManageRoster
    && hasAdminPermission(adminAccess, ADMIN_PERMISSIONS.MONEY_READ)
  )
  const canViewMoneyData = hasAdminPermission(adminAccess, ADMIN_PERMISSIONS.MONEY_READ)
  const currentWorkspaceContextKey = currentAdminDataContextKey
  const {
    bookings,
    bookingsError,
    bookingsLoadState,
    moneyError,
    moneyLedger,
    moneyLoadState,
    refreshAll: refreshLedgers,
    retryBookings,
    retryMoney,
    retryWaitlist,
    waitlistEntries,
    waitlistError,
    waitlistLoadState,
  } = useAdminOfficialGameLedgers({
    canViewMoneyData,
    currentUser,
    gameId,
    isAdminAccessLoading,
  })
  const canViewChat = hasAdminPermission(adminAccess, ADMIN_PERMISSIONS.CONTENT_MODERATE)
  const canViewAudit = hasAnyAdminPermission(adminAccess, [
    ADMIN_PERMISSIONS.AUDIT_READ,
    ADMIN_PERMISSIONS.AUDIT_SUPPORT_READ,
  ])
  const canCancelGame = hasAdminPermission(
    adminAccess,
    ADMIN_PERMISSIONS.OFFICIAL_GAMES_CANCEL,
  )
  const visibleManageTabs = manageTabs
  const selectedTab = visibleManageTabs.some((tab) => tab.id === activeTab)
    ? activeTab
    : visibleManageTabs[0]?.id || 'roster'
  const workspaceIsCurrent = workspaceContextKey === currentWorkspaceContextKey
  const chatIsCurrent = chatContextKey === currentAdminDataContextKey
  const auditIsCurrent = auditContextKey === currentAdminDataContextKey
  const visibleChatRooms = chatIsCurrent ? chatRooms : []
  const visibleChatMessages = chatIsCurrent ? chatMessages : []
  const visibleChatError = chatIsCurrent ? chatError : ''
  const visibleChatLoadState = chatIsCurrent ? chatLoadState : 'loading'
  const visibleAuditActions = auditIsCurrent ? auditActions : []
  const visibleAuditError = auditIsCurrent ? auditError : ''
  const visibleAuditLoadState = auditIsCurrent ? auditLoadState : 'loading'

  async function refreshWorkspace() {
    const [gameResponse, participantResponse] = await Promise.all([
      getAdminOfficialGame({ firebaseUser: currentUser, gameId }),
      listAdminOfficialGameParticipants({ firebaseUser: currentUser, gameId }),
    ])
    const nextVenueImages = gameResponse.game.venue_id
      ? await listOfficialGameVenueImages({
        venueId: gameResponse.game.venue_id,
      }).catch(() => [])
      : []

    setGame(gameResponse.game)
    setParticipants(participantResponse ?? [])
    setVenueImages(nextVenueImages ?? [])
    refreshLedgers()
    setChatRefreshCount((count) => count + 1)
    setAuditRefreshCount((count) => count + 1)
  }

  useEffect(() => {
    if (isAdminAccessLoading || !currentUser) {
      return undefined
    }

    let isMounted = true

    async function loadWorkspace() {
      setPageError('')
      setLoadState('loading')

      try {
        const [
          gameResponse,
          participantResponse,
        ] = await Promise.all([
          getAdminOfficialGame({ firebaseUser: currentUser, gameId }),
          listAdminOfficialGameParticipants({ firebaseUser: currentUser, gameId }),
        ])
        if (!isMounted) {
          return
        }

        const nextVenueImages = gameResponse.game.venue_id
          ? await listOfficialGameVenueImages({
            venueId: gameResponse.game.venue_id,
          }).catch(() => [])
          : []

        if (!isMounted) {
          return
        }

        setGame(gameResponse.game)
        setParticipants(participantResponse ?? [])
        setVenueImages(nextVenueImages ?? [])
        setWorkspaceContextKey(currentWorkspaceContextKey)
        setPageError('')
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setPageError(error.message || 'Official game could not be loaded.')
        setWorkspaceContextKey(currentWorkspaceContextKey)
        setLoadState('error')
      }
    }

    loadWorkspace()

    return () => {
      isMounted = false
    }
  }, [
    currentUser,
    currentWorkspaceContextKey,
    gameId,
    isAdminAccessLoading,
  ])

  useEffect(() => {
    if (isAdminAccessLoading || !currentUser) {
      return undefined
    }

    if (!canViewChat) {
      return undefined
    }

    let isMounted = true

    async function loadChat() {
      setChatRooms([])
      setChatMessages([])
      setChatError('')
      setChatLoadState('loading')

      try {
        const nextChatRooms = await listAdminOfficialGameChatRooms({
          firebaseUser: currentUser,
          gameId,
        })
        const safeChatRooms = nextChatRooms ?? []
        const activeChat = getPrimaryGameChat(safeChatRooms)
        if (!isMounted) {
          return
        }
        const nextChatMessages = activeChat
          ? await listAdminOfficialGameChatMessages({
            chatId: activeChat.id,
            firebaseUser: currentUser,
            limit: 50,
          })
          : []

        if (!isMounted) {
          return
        }

        setChatRooms(safeChatRooms)
        setChatMessages(nextChatMessages ?? [])
        setChatContextKey(currentAdminDataContextKey)
        setChatError('')
        setChatLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setChatRooms([])
        setChatMessages([])
        setChatContextKey(currentAdminDataContextKey)
        setChatError(error.message || 'Chat could not be loaded.')
        setChatLoadState('error')
      }
    }

    loadChat()

    return () => {
      isMounted = false
    }
  }, [
    canViewChat,
    chatRefreshCount,
    currentAdminDataContextKey,
    currentUser,
    gameId,
    isAdminAccessLoading,
  ])

  useEffect(() => {
    if (isAdminAccessLoading || !currentUser) {
      return undefined
    }

    if (!canViewAudit) {
      return undefined
    }

    let isMounted = true

    async function loadAuditActions() {
      setAuditActions([])
      setAuditError('')
      setAuditLoadState('loading')

      try {
        const nextActions = await listAdminActions({
          firebaseUser: currentUser,
          limit: 100,
          targetGameId: gameId,
        })
        if (!isMounted) {
          return
        }

        setAuditActions(nextActions ?? [])
        setAuditContextKey(currentAdminDataContextKey)
        setAuditError('')
        setAuditLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setAuditActions([])
        setAuditContextKey(currentAdminDataContextKey)
        setAuditError(error.message || 'Audit actions could not be loaded.')
        setAuditLoadState('error')
      }
    }

    loadAuditActions()

    return () => {
      isMounted = false
    }
  }, [
    auditRefreshCount,
    canViewAudit,
    currentAdminDataContextKey,
    currentUser,
    gameId,
    isAdminAccessLoading,
  ])

  useEffect(() => {
    if (!pageNotice) {
      return undefined
    }

    const timerId = window.setTimeout(() => setPageNotice(''), 3600)
    return () => window.clearTimeout(timerId)
  }, [pageNotice])

  async function runMutation(action, successMessage) {
    setMutationState('saving')
    setPageError('')
    setPageNotice('')

    try {
      await action()
      await refreshWorkspace()
      setPageNotice(successMessage)
      return true
    } catch (error) {
      setPageError(error.message || 'Admin change could not be saved.')
      return false
    } finally {
      setMutationState('idle')
    }
  }

  function handleAssignHost({ hostUserId, reason }) {
    return runMutation(
      () => assignAdminOfficialGameHost({
        firebaseUser: currentUser,
        gameId,
        hostUserId,
        reason,
      }),
      'Host updated.',
    )
  }

  function handleRemoveHost(reason) {
    return runMutation(
      () => removeAdminOfficialGameHost({
        firebaseUser: currentUser,
        gameId,
        reason,
      }),
      'Host removed.',
    )
  }

  function handleAddPlayer({ userId, reason }) {
    return runMutation(
      () => addAdminOfficialGamePlayer({
        firebaseUser: currentUser,
        gameId,
        userId,
        reason,
      }),
      'Player added.',
    )
  }

  const handleSearchRosterUsers = useCallback(({ query, signal }) => {
    return searchAdminOfficialGameUsers({
      firebaseUser: currentUser,
      gameId,
      query,
      signal,
    })
  }, [currentUser, gameId])

  function handleRemovePlayer({ participant, reason }) {
    return runMutation(
      () => removeAdminOfficialGamePlayer({
        firebaseUser: currentUser,
        gameId,
        participantId: participant.id,
        reason,
      }),
      'Player removed.',
    )
  }

  async function handlePreviewRemoval(participant) {
    const requestId = removalPreviewRequestIdRef.current + 1
    removalPreviewRequestIdRef.current = requestId
    setPreviewParticipant(participant)
    setRemovalPreview(null)
    setRemovalPreviewError('')
    setRemovalPreviewState('loading')
    setRemovalExecutionResult(null)
    setRemovalExecutionError('')
    setRemovalExecutionState('idle')

    try {
      const preview = await previewAdminOfficialGamePlayerRemoval({
        firebaseUser: currentUser,
        gameId,
        participantId: participant.id,
      })
      if (removalPreviewRequestIdRef.current !== requestId) {
        return
      }

      setRemovalPreview(preview)
      setRemovalPreviewState('ready')
    } catch (error) {
      if (removalPreviewRequestIdRef.current !== requestId) {
        return
      }

      setRemovalPreviewError(error.message || 'Removal impact could not be loaded.')
      setRemovalPreviewState('error')
    }
  }

  const handleCloseRemovalPreview = useCallback(() => {
    if (removalExecutionState === 'saving') {
      return
    }

    removalPreviewRequestIdRef.current += 1
    setPreviewParticipant(null)
    setRemovalPreview(null)
    setRemovalPreviewError('')
    setRemovalPreviewState('idle')
    setRemovalExecutionResult(null)
    setRemovalExecutionError('')
    setRemovalExecutionState('idle')
  }, [removalExecutionState])

  async function handleExecuteRemoval({ outcome, reason }) {
    if (!previewParticipant || !removalPreview) {
      return
    }

    setRemovalExecutionError('')
    setRemovalExecutionState('saving')
    try {
      const result = await executeAdminOfficialGamePlayerRemoval({
        firebaseUser: currentUser,
        gameId,
        participantId: previewParticipant.id,
        previewToken: removalPreview.preview_token,
        outcome,
        reason,
      })
      setRemovalExecutionResult(result)
      await refreshWorkspace()
      setPageNotice(
        result.refund_follow_up_required
          ? 'Player removed. Refund follow-up is required.'
          : 'Player removal completed.',
      )
    } catch (error) {
      if (error.status === 409) {
        try {
          const refreshedPreview = await previewAdminOfficialGamePlayerRemoval({
            firebaseUser: currentUser,
            gameId,
            participantId: previewParticipant.id,
          })
          setRemovalPreview(refreshedPreview)
        } catch {
          setRemovalPreview(null)
        }
      }
      setRemovalExecutionError(error.message || 'Player removal could not be completed.')
    } finally {
      setRemovalExecutionState('idle')
    }
  }

  async function loadCancelPreview() {
    const requestId = cancelPreviewRequestIdRef.current + 1
    cancelPreviewRequestIdRef.current = requestId
    setCancelPreview(null)
    setCancelPreviewState('loading')
    setCancelError('')

    try {
      const preview = await previewAdminOfficialGameCancellation({
        firebaseUser: currentUser,
        gameId,
      })
      if (cancelPreviewRequestIdRef.current !== requestId) {
        return null
      }

      setCancelPreview(preview)
      setCancelPreviewState('ready')
      return preview
    } catch (error) {
      if (cancelPreviewRequestIdRef.current !== requestId) {
        return null
      }

      setCancelError(error.message || 'Cancellation impact could not be loaded.')
      setCancelPreviewState('error')
      return null
    }
  }

  function handleOpenCancelModal() {
    setIsCancelModalOpen(true)
    setCancelReason('')
    setCancelResult(null)
    loadCancelPreview()
  }

  function handleCloseCancelModal() {
    if (isMutating) {
      return
    }

    cancelPreviewRequestIdRef.current += 1
    setIsCancelModalOpen(false)
    setCancelReason('')
    setCancelPreview(null)
    setCancelPreviewState('idle')
    setCancelError('')
    setCancelResult(null)
  }

  async function handleCancelGame() {
    if (!cancelPreview?.preview_token) {
      return
    }

    setMutationState('saving')
    setPageError('')
    setPageNotice('')
    setCancelError('')

    try {
      const result = await cancelAdminOfficialGame({
        cancelReason: cancelReason.trim(),
        firebaseUser: currentUser,
        gameId,
        previewToken: cancelPreview.preview_token,
      })
      setCancelResult(result)
      setGame(result.game)
      await refreshWorkspace()
      setPageNotice(
        result.refund_follow_up_required || result.payment_follow_up_required
          ? 'Official game cancelled. Money follow-up is required.'
          : 'Official game cancelled.',
      )
    } catch (error) {
      if (error.status === 409) {
        await loadCancelPreview()
      }
      setCancelError(error.message || 'Official game could not be cancelled.')
    } finally {
      setMutationState('idle')
    }
  }

  function handleCreateReplacementGame() {
    navigate(`/admin/official-games/new?replace_game_id=${encodeURIComponent(gameId)}`)
  }

  const cancelDisabledReason = getCancelDisabledReason(game)
  const isMutating = mutationState === 'saving'
  const canExecuteRemoval = Boolean(
    removalPreview?.required_permissions?.every((permission) =>
      hasAdminPermission(adminAccess, permission),
    ),
  )

  return (
    <>
      <AdminWorkspaceLayout
        actions={(
          <div className="admin-official-header-actions">
            <Link className="admin-official-button" to="/admin/official-games">
              <ArrowLeftIcon />
              Back
            </Link>
            {workspaceIsCurrent && game?.id === gameId && canEditGame && (
              <Link
                className="admin-official-button"
                to={`/admin/official-games/${gameId}/edit`}
              >
                <PencilIcon />
                Edit game
              </Link>
            )}
            {workspaceIsCurrent && game?.id === gameId && canCancelGame && (
              <button
                className="admin-official-button admin-official-button--danger"
                disabled={isMutating || Boolean(cancelDisabledReason)}
                title={cancelDisabledReason || 'Cancel game'}
                type="button"
                onClick={handleOpenCancelModal}
              >
                <TrashIcon />
                Cancel game
              </button>
            )}
          </div>
        )}
        breadcrumbs={['Admin', 'Games', 'Official Games']}
        description="Review roster, host, money, and lifecycle details."
        icon={ShieldCheckIcon}
        title="Manage Official Game"
      >
        {workspaceIsCurrent && pageError && (
          <p className="admin-official-alert">{pageError}</p>
        )}
        {workspaceIsCurrent && pageNotice && (
          <p className="admin-official-notice admin-official-toast" role="status" aria-live="polite">
            {pageNotice}
          </p>
        )}

        {(!workspaceIsCurrent || loadState === 'loading') && (
          <p className="admin-official-empty">Loading game.</p>
        )}
        {workspaceIsCurrent && loadState === 'ready' && game?.id === gameId && (
          <div className="admin-official-detail-layout">
            <AdminOfficialGameSummary game={game} participants={participants} />

            <nav className="admin-manage-tabs" aria-label="Official game management">
              {visibleManageTabs.map((tab) => (
                <button
                  key={tab.id}
                  className={selectedTab === tab.id ? 'is-active' : ''}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.label}
                </button>
              ))}
            </nav>

            {selectedTab === 'roster' && (
              <section className="admin-manage-roster-layout" aria-label="Official game roster">
                <AdminOfficialGameHostPanel
                  key={`${game.updated_at}-${game.host_user_id ?? 'unassigned'}`}
                  canAssignHost={canManageRoster}
                  canRemoveHost={canManageRoster}
                  game={game}
                  isSaving={isMutating}
                  participants={participants}
                  onAssignHost={handleAssignHost}
                  onRemoveHost={handleRemoveHost}
                />
                <AdminOfficialGameRosterPanel
                  canAddPlayer={canSearchRosterUsers}
                  canManageRoster={canManageRoster}
                  canPreviewRemovals={canPreviewRemovals}
                  game={game}
                  isSaving={isMutating}
                  participants={participants}
                  onAddPlayer={handleAddPlayer}
                  onPreviewRemoval={handlePreviewRemoval}
                  onRemovePlayer={handleRemovePlayer}
                  onSearchUsers={handleSearchRosterUsers}
                />
              </section>
            )}

            {selectedTab === 'bookings' && (
              canViewMoneyData ? (
                <AdminOfficialGameBookingsTab
                  bookings={bookings}
                  error={bookingsError}
                  loadState={bookingsLoadState}
                  onRetry={retryBookings}
                  participants={participants}
                />
              ) : (
                <AdminOfficialGameLockedTab
                  description="Money read permission is required for booking details."
                  icon={ClipboardListIcon}
                  label="Official game bookings"
                  title="Bookings"
                />
              )
            )}

            {selectedTab === 'waitlist' && (
              canViewMoneyData ? (
                <AdminOfficialGameWaitlistTab
                  error={waitlistError}
                  game={game}
                  loadState={waitlistLoadState}
                  onRetry={retryWaitlist}
                  participants={participants}
                  waitlistEntries={waitlistEntries}
                />
              ) : (
                <AdminOfficialGameLockedTab
                  description="Money read permission is required for waitlist details."
                  icon={UsersIcon}
                  label="Official game waitlist"
                  title="Waitlist"
                />
              )
            )}

            {selectedTab === 'money' && (
              canViewMoneyData ? (
                <AdminOfficialGameMoneyTab
                  error={moneyError}
                  game={game}
                  loadState={moneyLoadState}
                  moneyLedger={moneyLedger}
                  onRetry={retryMoney}
                  participants={participants}
                />
              ) : (
                <AdminOfficialGameLockedTab
                  description="Money read permission is required for money ledger details."
                  icon={DollarIcon}
                  label="Official game money ledger"
                  title="Payments, Refunds, Credits"
                />
              )
            )}

            {selectedTab === 'chat' && (
              canViewChat ? (
                <AdminOfficialGameChatTab
                  chatLoadState={visibleChatLoadState}
                  chatMessages={visibleChatMessages}
                  chatRooms={visibleChatRooms}
                  error={visibleChatError}
                  game={game}
                  participants={participants}
                />
              ) : (
                <AdminOfficialGameLockedTab
                  description="Content moderation permission is required for chat inspection."
                  icon={ChatIcon}
                  label="Official game chat"
                  title="Chat"
                />
              )
            )}

            {selectedTab === 'photos' && (
              <AdminOfficialGamePhotosTab venueImages={venueImages} />
            )}

            {selectedTab === 'audit' && (
              canViewAudit ? (
                <AdminOfficialGameAuditTab
                  actions={visibleAuditActions}
                  error={visibleAuditError}
                  loadState={visibleAuditLoadState}
                  participants={participants}
                />
              ) : (
                <AdminOfficialGameLockedTab
                  description="Audit permission is required for game action history."
                  icon={ClipboardListIcon}
                  label="Official game activity"
                  title="Activity"
                />
              )
            )}
          </div>
        )}
      </AdminWorkspaceLayout>

      {workspaceIsCurrent && isCancelModalOpen && game?.id === gameId && (
        <AdminOfficialGameCancelModal
          cancelReason={cancelReason}
          error={cancelError}
          game={game}
          isLoadingPreview={cancelPreviewState === 'loading'}
          isCancelling={isMutating}
          onCancelReasonChange={setCancelReason}
          onClose={handleCloseCancelModal}
          onConfirm={handleCancelGame}
          onCreateReplacement={handleCreateReplacementGame}
          preview={cancelPreview}
          result={cancelResult}
        />
      )}

      {workspaceIsCurrent && previewParticipant && (
        <AdminOfficialGameRemovalPreviewModal
          error={removalPreviewError}
          executionError={removalExecutionError}
          executionResult={removalExecutionResult}
          canExecute={canExecuteRemoval}
          isExecuting={removalExecutionState === 'saving'}
          isLoading={removalPreviewState === 'loading'}
          preview={removalPreview}
          selectedParticipant={previewParticipant}
          onClose={handleCloseRemovalPreview}
          onExecute={handleExecuteRemoval}
        />
      )}
    </>
  )
}

function AdminOfficialGamePage() {
  const { gameId } = useParams()

  return <AdminOfficialGamePageContent gameId={gameId} key={gameId} />
}

export default AdminOfficialGamePage
