import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldAlert,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { AppPageHeader, AppPageShell } from '../../../components/app/index.js'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminCommunityGames.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { listAdminCommunityGames } from '../shared/adminApi.js'
import {
  formatAdminCommunityDateTime,
  formatAdminCommunityMoney,
  formatAdminCommunityStatus,
  shortAdminCommunityId,
} from './adminCommunityGameFormatters.js'

const GAME_STATUS_OPTIONS = [
  { label: 'All statuses', value: '' },
  { label: 'Scheduled', value: 'scheduled' },
  { label: 'Full', value: 'full' },
  { label: 'Cancelled', value: 'cancelled' },
  { label: 'Completed', value: 'completed' },
  { label: 'Abandoned', value: 'abandoned' },
]

const PUBLISH_STATUS_OPTIONS = [
  { label: 'All publishing', value: '' },
  { label: 'Draft', value: 'draft' },
  { label: 'Published', value: 'published' },
  { label: 'Archived', value: 'archived' },
]

const EMPTY_FILTERS = {
  gameStatus: '',
  publishStatus: '',
  query: '',
}

const PAGE_SIZE = 50

function getModerationPaymentTextLabel(game) {
  if (game.moderation_state.unsafe_payment_text_hidden) {
    return 'Payment text hidden'
  }

  return game.moderation_state.host_payment_snapshot_present
    ? 'Payment text present'
    : 'No payment text'
}

function AdminCommunityGamesLoading() {
  return (
    <div
      aria-label="Loading community games"
      className="admin-community-loading"
      role="status"
    >
      {Array.from({ length: 5 }).map((_, index) => (
        <div className="admin-community-loading__row" key={index}>
          <SkeletonBlock height="0.92rem" rounded width="42%" />
          <SkeletonBlock height="0.72rem" rounded width="65%" />
          <SkeletonBlock height="0.72rem" rounded width="28%" />
        </div>
      ))}
    </div>
  )
}

function AdminCommunityGamesList({ games }) {
  if (!games.length) {
    return (
      <div className="admin-community-empty">
        <strong>No community games found</strong>
        <span>Adjust the search or filters.</span>
      </div>
    )
  }

  return (
    <div className="admin-community-table" role="table" aria-label="Community games">
      <div className="admin-community-table__header" role="row">
        <span role="columnheader">Game</span>
        <span role="columnheader">Host</span>
        <span role="columnheader">Roster</span>
        <span role="columnheader">Payment</span>
        <span role="columnheader">Moderation</span>
      </div>
      {games.map((game) => (
        <Link
          aria-label={`Open ${game.title}`}
          className="admin-community-table__row"
          key={game.id}
          role="row"
          to={`/admin/community-games/${game.id}`}
        >
          <div className="admin-community-table__identity" data-label="Game" role="cell">
            <strong>{game.title}</strong>
            <span>
              {game.city}, {game.state} ·{' '}
              {formatAdminCommunityDateTime(game.starts_at, game.timezone)}
            </span>
            <code>{shortAdminCommunityId(game.id)}</code>
          </div>
          <div data-label="Host" role="cell">
            <strong>{game.host?.display_name || 'No host'}</strong>
            <span>{formatAdminCommunityStatus(game.host?.hosting_status)}</span>
          </div>
          <div data-label="Roster" role="cell">
            <strong>
              {game.participant_summary.confirmed_count}/{game.total_spots}
            </strong>
            <span>{game.participant_summary.guest_count} guests</span>
          </div>
          <div data-label="Payment" role="cell">
            <strong>
              {formatAdminCommunityMoney(game.price_per_player_cents)}
            </strong>
            <span>{formatAdminCommunityStatus(game.payment_collection_type)}</span>
          </div>
          <div data-label="Moderation" role="cell">
            <span className={`admin-community-status admin-community-status--${game.game_status}`}>
              {formatAdminCommunityStatus(game.game_status)}
            </span>
            <span>{formatAdminCommunityStatus(game.publish_status)}</span>
            <span
              className={
                game.moderation_state.review_flag_status === 'open'
                  ? 'admin-community-review-state admin-community-review-state--open'
                  : 'admin-community-review-state'
              }
            >
              {game.moderation_state.review_flag_status === 'not_flagged'
                ? 'No review flag'
                : `Review ${formatAdminCommunityStatus(
                    game.moderation_state.review_flag_status,
                  )}`}
            </span>
            <span>{getModerationPaymentTextLabel(game)}</span>
          </div>
        </Link>
      ))}
    </div>
  )
}

function AdminCommunityGamesPage() {
  const { currentUser } = useAuth()
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS)
  const [games, setGames] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadGames() {
      if (!currentUser) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const response = await listAdminCommunityGames({
          firebaseUser: currentUser,
          limit: PAGE_SIZE,
          offset,
          ...appliedFilters,
        })

        if (!isMounted) {
          return
        }

        const nextGames = response.games ?? []
        const nextTotalCount = response.total_count ?? nextGames.length
        if (!nextGames.length && offset > 0 && nextTotalCount > 0) {
          setOffset(Math.max(0, offset - PAGE_SIZE))
          return
        }

        setGames(nextGames)
        setTotalCount(nextTotalCount)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setGames([])
        setTotalCount(0)
        setPageError(error.message || 'Community games could not be loaded.')
        setLoadState('error')
      }
    }

    loadGames()

    return () => {
      isMounted = false
    }
  }, [appliedFilters, currentUser, offset, refreshCount])

  function updateDraftFilter(field, value) {
    setDraftFilters((current) => ({
      ...current,
      [field]: value,
    }))
  }

  function handleSearch(event) {
    event.preventDefault()
    setOffset(0)
    setAppliedFilters({
      ...draftFilters,
      query: draftFilters.query.trim(),
    })
  }

  function handleReset() {
    setDraftFilters(EMPTY_FILTERS)
    setAppliedFilters(EMPTY_FILTERS)
    setOffset(0)
  }

  const pageStart = totalCount ? offset + 1 : 0
  const pageEnd = Math.min(offset + games.length, totalCount)
  const hasPreviousPage = offset > 0
  const hasNextPage = offset + games.length < totalCount

  return (
    <AppPageShell className="admin-page" mainClassName="admin-shell admin-community-shell">
      <AppPageHeader subtitle="Admin" title="Community Games" />

      <AdminWorkspaceLayout>
        <div className="admin-community-layout">
          <section className="admin-community-panel" aria-label="Community game search">
            <div className="admin-community-panel__heading">
              <div>
                <ShieldAlert />
                <h2>Game support</h2>
              </div>
              <span>{loadState === 'ready' ? totalCount : 0} results</span>
            </div>

            <form className="admin-community-filters" onSubmit={handleSearch}>
              <label className="admin-community-filters__search">
                <span>Search</span>
                <input
                  aria-label="Search by title, host, city, or game ID"
                  value={draftFilters.query}
                  onChange={(event) => updateDraftFilter('query', event.target.value)}
                />
              </label>
              <label>
                <span>Status</span>
                <select
                  value={draftFilters.gameStatus}
                  onChange={(event) => updateDraftFilter('gameStatus', event.target.value)}
                >
                  {GAME_STATUS_OPTIONS.map((option) => (
                    <option key={option.label} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>Publish</span>
                <select
                  value={draftFilters.publishStatus}
                  onChange={(event) => updateDraftFilter('publishStatus', event.target.value)}
                >
                  {PUBLISH_STATUS_OPTIONS.map((option) => (
                    <option key={option.label} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <div className="admin-community-filter-actions">
                <button className="admin-community-button" type="submit">
                  <Search />
                  Search
                </button>
                <button
                  className="admin-community-button"
                  type="button"
                  onClick={handleReset}
                >
                  <RotateCcw />
                  Reset
                </button>
                <button
                  aria-label="Refresh community games"
                  className="admin-community-button admin-community-button--icon"
                  type="button"
                  onClick={() => setRefreshCount((count) => count + 1)}
                >
                  <RefreshCw />
                </button>
              </div>
            </form>

            {pageError && (
              <FormErrorMessage className="admin-community-page-error">
                {pageError}
              </FormErrorMessage>
            )}
            {loadState === 'loading' ? (
              <AdminCommunityGamesLoading />
            ) : loadState === 'ready' ? (
              <>
                <AdminCommunityGamesList games={games} />
                {totalCount > PAGE_SIZE && (
                  <nav
                    aria-label="Community games pagination"
                    className="admin-community-pagination"
                  >
                    <span>{pageStart}-{pageEnd} of {totalCount}</span>
                    <div>
                      <button
                        aria-label="Previous community games page"
                        className="admin-community-button admin-community-button--icon"
                        disabled={!hasPreviousPage}
                        title="Previous page"
                        type="button"
                        onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                      >
                        <ChevronLeft />
                      </button>
                      <button
                        aria-label="Next community games page"
                        className="admin-community-button admin-community-button--icon"
                        disabled={!hasNextPage}
                        title="Next page"
                        type="button"
                        onClick={() => setOffset(offset + PAGE_SIZE)}
                      >
                        <ChevronRight />
                      </button>
                    </div>
                  </nav>
                )}
              </>
            ) : null}
          </section>
        </div>
      </AdminWorkspaceLayout>
    </AppPageShell>
  )
}

export default AdminCommunityGamesPage
