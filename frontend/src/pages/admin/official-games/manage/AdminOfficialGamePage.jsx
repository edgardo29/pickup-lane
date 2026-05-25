import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  CalendarIcon,
  ChatIcon,
  MapPinIcon,
  PriceTagIcon,
  ShieldCheckIcon,
  UsersIcon,
} from '../../../../components/BrowseIcons.jsx'
import { AppPageHeader, AppPageShell } from '../../../../components/app/index.js'
import { useAuth } from '../../../../hooks/useAuth.js'
import { buildMediaUrl } from '../../../../lib/apiClient.js'
import '../../../../styles/admin/AdminOfficialGames.css'
import AdminWorkspaceLayout from '../../shared/AdminWorkspaceLayout.jsx'
import AdminOfficialGameForm from '../shared/AdminOfficialGameForm.jsx'
import AdminOfficialGameHostPanel from './AdminOfficialGameHostPanel.jsx'
import AdminOfficialGameRosterPanel from './AdminOfficialGameRosterPanel.jsx'
import AdminOfficialGameSummary from './AdminOfficialGameSummary.jsx'
import {
  addAdminOfficialGamePlayer,
  assignAdminOfficialGameHost,
  cancelAdminOfficialGame,
  getAdminOfficialGame,
  listAdminVenueImages,
  listAdminOfficialGameParticipants,
  listAdminOfficialGameUsers,
  listAdminOfficialGameVenues,
  removeAdminOfficialGameHost,
  removeAdminOfficialGamePlayer,
  updateAdminOfficialGame,
} from '../shared/adminOfficialGamesApi.js'
import {
  formatAdminGameMoney,
  formatOfficialGameSchedule,
  getAdminUserLabel,
} from '../shared/adminOfficialGameForm.js'

const manageTabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'details', label: 'Details' },
  { id: 'roster', label: 'Roster' },
  { id: 'photos', label: 'Photos' },
]

const activeRosterStatuses = new Set(['confirmed', 'pending_payment'])
const cancellableGameStatuses = new Set(['scheduled', 'full'])

function getActiveRosterCount(participants) {
  return participants.filter((participant) =>
    activeRosterStatuses.has(participant.participant_status),
  ).length
}

function getControlsLabel(game) {
  return [
    game.allow_guests ? 'Guests on' : 'Guests off',
    game.waitlist_enabled ? 'Waitlist on' : 'Waitlist off',
    game.is_chat_enabled ? 'Chat on' : 'Chat off',
  ].join(' · ')
}

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

function OverviewFact({ icon, label, value }) {
  return (
    <div className="admin-manage-fact">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function AdminOfficialGameCancelModal({
  cancelReason,
  game,
  isCancelling,
  onCancelReasonChange,
  onClose,
  onConfirm,
}) {
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
          <h2 id="admin-cancel-official-game-title">Cancel official game?</h2>
          <p>{game.title} will be cancelled for everyone. Players are notified and active app payments are marked for refund.</p>
        </div>

        <label className="admin-official-textarea-field">
          <span>Internal reason</span>
          <textarea
            maxLength={280}
            placeholder="Optional cancellation reason"
            value={cancelReason}
            onChange={(event) => onCancelReasonChange(event.target.value)}
          />
          <small>{cancelReason.length}/280</small>
        </label>

        <div className="admin-official-confirm-modal__actions">
          <button
            className="admin-official-button"
            disabled={isCancelling}
            type="button"
            onClick={onClose}
          >
            Keep game
          </button>
          <button
            className="admin-official-button admin-official-button--danger-solid"
            disabled={isCancelling}
            type="button"
            onClick={onConfirm}
          >
            {isCancelling ? 'Cancelling' : 'Cancel game'}
          </button>
        </div>
      </section>
    </div>
  )
}

function AdminOfficialGameOverview({ game, hostUser, participants, venueImages }) {
  const activeRosterCount = getActiveRosterCount(participants)

  return (
    <section className="admin-official-panel admin-manage-tab-panel" aria-label="Official game overview">
      <div className="admin-manage-overview-grid">
        <OverviewFact icon={<CalendarIcon />} label="Schedule" value={formatOfficialGameSchedule(game)} />
        <OverviewFact icon={<MapPinIcon />} label="Venue" value={game.venue_name_snapshot || 'Venue unavailable'} />
        <OverviewFact icon={<UsersIcon />} label="Roster" value={`${activeRosterCount} / ${game.total_spots}`} />
        <OverviewFact icon={<PriceTagIcon />} label="Price" value={formatAdminGameMoney(game.price_per_player_cents, game.currency)} />
        <OverviewFact icon={<ShieldCheckIcon />} label="Host" value={hostUser ? getAdminUserLabel(hostUser) : 'Unassigned'} />
        <OverviewFact icon={<ChatIcon />} label="Controls" value={getControlsLabel(game)} />
      </div>

      <div className="admin-manage-photo-preview" aria-label="Venue photo preview">
        {venueImages.slice(0, 3).map((image) => (
          <img key={image.id} src={buildMediaUrl(image.image_url)} alt="" />
        ))}
        {venueImages.length === 0 && <span>No venue photos added.</span>}
      </div>
    </section>
  )
}

function AdminOfficialGamePhotosTab({ venueImages }) {
  const primaryImage = venueImages.find((image) => image.is_primary) || venueImages[0]
  const galleryImages = venueImages.filter((image) => image.id !== primaryImage?.id)

  return (
    <section className="admin-official-panel admin-manage-tab-panel" aria-label="Official game photos">
      <div className="admin-manage-photos">
        <div>
          <h2>Primary</h2>
          {primaryImage ? (
            <img src={buildMediaUrl(primaryImage.image_url)} alt="" />
          ) : (
            <div className="admin-manage-photo-empty">No primary photo.</div>
          )}
        </div>

        <div>
          <h2>Gallery</h2>
          {galleryImages.length > 0 ? (
            <div className="admin-manage-gallery-grid">
              {galleryImages.map((image) => (
                <img key={image.id} src={buildMediaUrl(image.image_url)} alt="" />
              ))}
            </div>
          ) : (
            <div className="admin-manage-photo-empty">No gallery photos.</div>
          )}
        </div>
      </div>
    </section>
  )
}

function AdminOfficialGamePage() {
  const { currentUser } = useAuth()
  const { gameId } = useParams()
  const [game, setGame] = useState(null)
  const [participants, setParticipants] = useState([])
  const [users, setUsers] = useState([])
  const [venues, setVenues] = useState([])
  const [venueImages, setVenueImages] = useState([])
  const [activeTab, setActiveTab] = useState('overview')
  const [loadState, setLoadState] = useState('loading')
  const [mutationState, setMutationState] = useState('idle')
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false)
  const [cancelReason, setCancelReason] = useState('')
  const [pageError, setPageError] = useState('')
  const [pageNotice, setPageNotice] = useState('')

  const refreshWorkspace = useCallback(async () => {
    const [gameResponse, participantResponse] = await Promise.all([
      getAdminOfficialGame({ firebaseUser: currentUser, gameId }),
      listAdminOfficialGameParticipants({ firebaseUser: currentUser, gameId }),
    ])
    const nextVenueImages = gameResponse.game.venue_id
      ? await listAdminVenueImages({
        firebaseUser: currentUser,
        venueId: gameResponse.game.venue_id,
      }).catch(() => [])
      : []

    setGame(gameResponse.game)
    setParticipants(participantResponse ?? [])
    setVenueImages(nextVenueImages ?? [])
  }, [currentUser, gameId])

  useEffect(() => {
    let isMounted = true

    Promise.all([
      getAdminOfficialGame({ firebaseUser: currentUser, gameId }),
      listAdminOfficialGameParticipants({ firebaseUser: currentUser, gameId }),
      listAdminOfficialGameUsers({ firebaseUser: currentUser }),
      listAdminOfficialGameVenues({ firebaseUser: currentUser }),
    ])
      .then(async ([gameResponse, participantResponse, userResponse, venueResponse]) => {
        if (!isMounted) {
          return
        }

        const nextVenueImages = gameResponse.game.venue_id
          ? await listAdminVenueImages({
            firebaseUser: currentUser,
            venueId: gameResponse.game.venue_id,
          }).catch(() => [])
          : []

        if (!isMounted) {
          return
        }

        setGame(gameResponse.game)
        setParticipants(participantResponse ?? [])
        setUsers(userResponse ?? [])
        setVenues(venueResponse ?? [])
        setVenueImages(nextVenueImages ?? [])
        setPageError('')
        setLoadState('ready')
      })
      .catch((error) => {
        if (!isMounted) {
          return
        }

        setPageError(error.message || 'Official game could not be loaded.')
        setLoadState('error')
      })

    return () => {
      isMounted = false
    }
  }, [currentUser, gameId])

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

  function handleUpdateGame(payload) {
    return runMutation(
      () => updateAdminOfficialGame({
        firebaseUser: currentUser,
        gameId,
        payload,
      }),
      'Official game updated.',
    )
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

  async function handleCancelGame() {
    const wasCancelled = await runMutation(
      () => cancelAdminOfficialGame({
        cancelReason: cancelReason.trim(),
        firebaseUser: currentUser,
        gameId,
      }),
      'Official game cancelled.',
    )

    if (wasCancelled) {
      setIsCancelModalOpen(false)
      setCancelReason('')
    }
  }

  const hostUser = users.find((user) => user.id === game?.host_user_id)
  const cancelDisabledReason = getCancelDisabledReason(game)
  const isMutating = mutationState === 'saving'

  return (
    <AppPageShell className="admin-page" mainClassName="admin-shell admin-official-shell">
      <AppPageHeader
        actions={(
          <div className="admin-official-header-actions">
            <Link className="admin-official-button" to="/admin/official-games">
              Back
            </Link>
            {game && (
              <button
                className="admin-official-button admin-official-button--danger"
                disabled={isMutating || Boolean(cancelDisabledReason)}
                title={cancelDisabledReason || 'Cancel game'}
                type="button"
                onClick={() => setIsCancelModalOpen(true)}
              >
                Cancel game
              </button>
            )}
          </div>
        )}
        subtitle={game?.title || 'Admin'}
        title="Manage Official Game"
      />

      <AdminWorkspaceLayout>
        {pageError && <p className="admin-official-alert">{pageError}</p>}
        {pageNotice && (
          <p className="admin-official-notice admin-official-toast" role="status" aria-live="polite">
            {pageNotice}
          </p>
        )}

        {loadState === 'loading' && <p className="admin-official-empty">Loading game.</p>}
        {loadState === 'ready' && game && (
          <div className="admin-official-detail-layout">
            <AdminOfficialGameSummary game={game} participants={participants} />

            <nav className="admin-manage-tabs" aria-label="Official game management">
              {manageTabs.map((tab) => (
                <button
                  key={tab.id}
                  className={activeTab === tab.id ? 'is-active' : ''}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.label}
                </button>
              ))}
            </nav>

            {activeTab === 'overview' && (
              <AdminOfficialGameOverview
                game={game}
                hostUser={hostUser}
                participants={participants}
                venueImages={venueImages}
              />
            )}

            {activeTab === 'details' && (
              <section className="admin-official-panel admin-manage-tab-panel" aria-label="Edit official game">
                <AdminOfficialGameForm
                  key={game.updated_at}
                  game={game}
                  isSaving={isMutating}
                  submitLabel="Save changes"
                  venues={venues}
                  onSubmit={handleUpdateGame}
                />
              </section>
            )}

            {activeTab === 'roster' && (
              <section className="admin-manage-roster-layout" aria-label="Official game roster">
                <AdminOfficialGameHostPanel
                  key={`${game.updated_at}-${game.host_user_id ?? 'unassigned'}`}
                  game={game}
                  isSaving={isMutating}
                  users={users}
                  onAssignHost={handleAssignHost}
                  onRemoveHost={handleRemoveHost}
                />
                <AdminOfficialGameRosterPanel
                  game={game}
                  isSaving={isMutating}
                  participants={participants}
                  users={users}
                  onAddPlayer={handleAddPlayer}
                  onRemovePlayer={handleRemovePlayer}
                />
              </section>
            )}

            {activeTab === 'photos' && (
              <AdminOfficialGamePhotosTab venueImages={venueImages} />
            )}
          </div>
        )}
      </AdminWorkspaceLayout>

      {isCancelModalOpen && game && (
        <AdminOfficialGameCancelModal
          cancelReason={cancelReason}
          game={game}
          isCancelling={isMutating}
          onCancelReasonChange={setCancelReason}
          onClose={() => {
            if (!isMutating) {
              setIsCancelModalOpen(false)
            }
          }}
          onConfirm={handleCancelGame}
        />
      )}
    </AppPageShell>
  )
}

export default AdminOfficialGamePage
