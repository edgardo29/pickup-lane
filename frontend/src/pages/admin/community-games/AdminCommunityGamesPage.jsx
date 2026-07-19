import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Search,
  ShieldAlert,
  X,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import {
  AddressIcon,
  GameDateIcon,
  GameSpotsIcon,
  GameTimeIcon,
  VenueIcon,
} from '../../../components/GameFactIcons.jsx'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminCommunityGames.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { listAdminCommunityGames } from '../shared/adminApi.js'
import { formatAdminCommunityMoney } from './adminCommunityGameFormatters.js'

const communityGameViewTabs = [
  { key: 'active', label: 'Active' },
  { key: 'full', label: 'Full' },
  { key: 'completed', label: 'Completed' },
  { key: 'cancelled', label: 'Cancelled' },
  { key: 'expired', label: 'Expired' },
  { key: 'removed', label: 'Removed' },
]

const PAGE_SIZE = 24
const SEARCH_DEBOUNCE_MS = 300
const SEARCH_MIN_LENGTH = 3
const SEARCH_MAX_LENGTH = 120
const fallbackTimeZone = 'America/Chicago'

function useDebouncedValue(value, delayMs) {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedValue(value)
    }, delayMs)

    return () => window.clearTimeout(timeoutId)
  }, [delayMs, value])

  return debouncedValue
}

function getGameTimeZone(game) {
  return game.timezone || fallbackTimeZone
}

function getLocationLine(game) {
  return [game.city, game.state].filter(Boolean).join(', ') || 'Location unavailable'
}

function getVenueName(game) {
  return game.venue_name || game.venue_name_snapshot || game.venue?.name || ''
}

function formatTimeRange(game) {
  if (!game.starts_at || !game.ends_at) {
    return 'Time unavailable'
  }

  const formatter = new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    timeZone: getGameTimeZone(game),
  })

  return `${formatter.format(new Date(game.starts_at))} - ${formatter.format(
    new Date(game.ends_at),
  )}`
}

function getLocalDateKey(game) {
  if (game.starts_on_local) {
    return game.starts_on_local
  }

  if (!game.starts_at) {
    return 'unknown'
  }

  const parts = new Intl.DateTimeFormat('en-US', {
    day: '2-digit',
    month: '2-digit',
    timeZone: getGameTimeZone(game),
    year: 'numeric',
  }).formatToParts(new Date(game.starts_at))

  const dateParts = Object.fromEntries(
    parts.filter((part) => part.type !== 'literal').map((part) => [
      part.type,
      part.value,
    ]),
  )

  return `${dateParts.year}-${dateParts.month}-${dateParts.day}`
}

function formatDateGroupLabel(game) {
  if (game.starts_on_local) {
    return new Intl.DateTimeFormat(undefined, {
      day: 'numeric',
      month: 'short',
      timeZone: 'UTC',
      weekday: 'short',
      year: 'numeric',
    }).format(new Date(`${game.starts_on_local}T12:00:00Z`)).toUpperCase()
  }

  if (!game.starts_at) {
    return 'Date unavailable'
  }

  return new Intl.DateTimeFormat(undefined, {
    day: 'numeric',
    month: 'short',
    timeZone: getGameTimeZone(game),
    weekday: 'short',
    year: 'numeric',
  }).format(new Date(game.starts_at)).toUpperCase()
}

function groupGamesByDate(games) {
  const groups = []
  const groupsByKey = new Map()

  games.forEach((game) => {
    const key = getLocalDateKey(game)

    if (!groupsByKey.has(key)) {
      const group = {
        games: [],
        key,
        label: formatDateGroupLabel(game),
      }
      groupsByKey.set(key, group)
      groups.push(group)
    }

    groupsByKey.get(key).games.push(game)
  })

  return groups
}

function getCommunityGameIssues(game) {
  const issues = []

  if (game.enforcement_state?.public_visibility_status === 'hidden') {
    issues.push('Hidden')
  }

  if (game.enforcement_state?.join_enforcement_status === 'paused') {
    issues.push('Joining paused')
  }

  if (game.moderation_state?.review_flag_status === 'open') {
    issues.push('Review required')
  }

  if (game.moderation_state?.unsafe_payment_text_hidden) {
    issues.push('Payment text hidden')
  }

  return issues
}

function getCountLabel(visibleCount, totalCount) {
  if (!totalCount) {
    return '0 games'
  }

  if (visibleCount >= totalCount) {
    return `${totalCount} ${totalCount === 1 ? 'game' : 'games'}`
  }

  return `Showing ${visibleCount} of ${totalCount} games`
}

function AdminCommunityGamesLoading() {
  return (
    <div
      aria-label="Loading community games"
      className="admin-community-date-groups admin-community-date-groups--skeleton"
      role="status"
    >
      <section className="admin-community-date-group">
        <div className="admin-community-date-group__header">
          <SkeletonBlock height="1rem" rounded width="12rem" />
        </div>
        <div className="admin-community-card-grid">
          {Array.from({ length: 8 }).map((_, index) => (
            <article className="admin-community-game-card admin-community-game-card--skeleton" key={index}>
              <div className="admin-community-game-card__body">
                <SkeletonBlock height="1rem" rounded width="82%" />
                <SkeletonBlock height="0.78rem" rounded width="58%" />
                <SkeletonBlock height="0.78rem" rounded width="66%" />
                <SkeletonBlock height="0.78rem" rounded width="72%" />
              </div>
              <div className="admin-community-game-card__issues" />
              <div className="admin-community-game-card__footer">
                <SkeletonBlock height="0.84rem" rounded width="5.4rem" />
                <SkeletonBlock height="0.84rem" rounded width="3.4rem" />
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

function AdminCommunityGameCard({ game }) {
  const issues = getCommunityGameIssues(game)
  const venueName = getVenueName(game)

  return (
    <Link
      aria-label={`Open ${game.title}`}
      className="admin-community-game-card"
      to={`/admin/community-games/${game.id}`}
    >
      <div className="admin-community-game-card__body">
        <div className="admin-community-game-card__identity">
          <h3>{game.title || 'Community Game'}</h3>
          <p className="admin-community-game-card__host">
            <span>Host: {game.host?.display_name || 'No host'}</span>
          </p>
        </div>

        <div className="admin-community-game-card__details">
          {venueName && (
            <p className="admin-community-game-card__venue">
              <VenueIcon aria-hidden="true" />
              <span>{venueName}</span>
            </p>
          )}
          <p>
            <AddressIcon aria-hidden="true" />
            <span>{getLocationLine(game)}</span>
          </p>
          <p>
            <GameTimeIcon aria-hidden="true" />
            <span>{formatTimeRange(game)}</span>
          </p>
        </div>
      </div>

      <div
        aria-label={issues.length ? 'Community game issues' : undefined}
        className={
          issues.length
            ? 'admin-community-game-card__issues admin-community-game-card__issues--active'
            : 'admin-community-game-card__issues'
        }
      >
        {issues.slice(0, 2).map((issue) => (
          <span key={issue}>{issue}</span>
        ))}
      </div>

      <div className="admin-community-game-card__footer">
        <span className="admin-community-game-card__capacity">
          <GameSpotsIcon aria-hidden="true" />
          <span className="admin-community-game-card__capacity-copy">
            <strong>{game.participant_summary.confirmed_count}/{game.total_spots}</strong> spots
          </span>
        </span>
        <span>{formatAdminCommunityMoney(game.price_per_player_cents)}</span>
      </div>
    </Link>
  )
}

function AdminCommunityGamesList({ games, hasFilters = false }) {
  if (!games.length) {
    return (
      <div className="admin-community-empty">
        <ShieldAlert aria-hidden="true" />
        <strong>No community games found</strong>
        <span>
          {hasFilters
            ? 'Try clearing the search or changing views.'
            : 'Community games will appear here after players publish them.'}
        </span>
      </div>
    )
  }

  const groupedGames = groupGamesByDate(games)

  return (
    <div className="admin-community-date-groups">
      {groupedGames.map((group) => (
        <section className="admin-community-date-group" key={group.key}>
          <div className="admin-community-date-group__header">
            <h3>
              <GameDateIcon aria-hidden="true" />
              {group.label}
            </h3>
            <span>{group.games.length} {group.games.length === 1 ? 'game' : 'games'}</span>
          </div>

          <div className="admin-community-card-grid">
            {group.games.map((game) => (
              <AdminCommunityGameCard game={game} key={game.id} />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

function AdminCommunityGamesPage() {
  const { currentUser } = useAuth()
  const [searchInput, setSearchInput] = useState('')
  const [activeView, setActiveView] = useState('active')
  const [games, setGames] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [loadState, setLoadState] = useState('loading')
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [pageError, setPageError] = useState('')
  const [loadMoreError, setLoadMoreError] = useState('')
  const [nextCursor, setNextCursor] = useState('')
  const [hasMoreGames, setHasMoreGames] = useState(false)
  const requestIdRef = useRef(0)
  const debouncedSearchInput = useDebouncedValue(
    searchInput.trim(),
    SEARCH_DEBOUNCE_MS,
  )
  const activeSearch =
    debouncedSearchInput.length >= SEARCH_MIN_LENGTH ? debouncedSearchInput : ''

  useEffect(() => {
    let isMounted = true
    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId

    async function loadGames() {
      if (!currentUser) {
        return
      }

      setLoadState('loading')
      setGames([])
      setPageError('')
      setLoadMoreError('')
      setNextCursor('')
      setHasMoreGames(false)

      try {
        const response = await listAdminCommunityGames({
          firebaseUser: currentUser,
          limit: PAGE_SIZE,
          offset: 0,
          query: activeSearch,
          view: activeView,
        })

        if (!isMounted || requestId !== requestIdRef.current) {
          return
        }

        const nextGames = response.games ?? []
        const nextTotalCount = response.total_count ?? nextGames.length

        setGames(nextGames)
        setTotalCount(nextTotalCount)
        setNextCursor(response.next_cursor ?? '')
        setHasMoreGames(Boolean(response.has_more))
        setLoadState('ready')
      } catch (error) {
        if (!isMounted || requestId !== requestIdRef.current) {
          return
        }

        setGames([])
        setTotalCount(0)
        setNextCursor('')
        setHasMoreGames(false)
        setPageError(error.message || 'Community games could not be loaded.')
        setLoadState('error')
      }
    }

    loadGames()

    return () => {
      isMounted = false
    }
  }, [activeSearch, activeView, currentUser])

  async function loadMoreGames() {
    if (!currentUser || isLoadingMore || !hasMoreGames) {
      return
    }

    setIsLoadingMore(true)
    setLoadMoreError('')

    try {
      const response = await listAdminCommunityGames({
        firebaseUser: currentUser,
        limit: PAGE_SIZE,
        cursor: nextCursor,
        offset: games.length,
        query: activeSearch,
        view: activeView,
      })

      const nextGames = response.games ?? []
      setGames((currentGames) => [...currentGames, ...nextGames])
      setTotalCount(response.total_count ?? totalCount)
      setNextCursor(response.next_cursor ?? '')
      setHasMoreGames(Boolean(response.has_more))
    } catch (error) {
      setLoadMoreError(error.message || 'More community games could not be loaded.')
    } finally {
      setIsLoadingMore(false)
    }
  }

  const hasFilters = Boolean(activeSearch || activeView !== 'active')
  const countLabel = getCountLabel(games.length, totalCount)

  return (
    <>
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'Games', 'Community Games']}
        description="Find community games and review moderation or support context."
        icon={ShieldAlert}
        title="Community Games"
      >
        <div className="admin-community-layout">
          <section className="admin-community-panel admin-community-panel--list" aria-label="Community game search">
            <div className="admin-community-view-tabs" aria-label="Community game views" role="tablist">
              {communityGameViewTabs.map((tab) => (
                <button
                  aria-selected={activeView === tab.key}
                  className={activeView === tab.key ? 'is-active' : ''}
                  key={tab.key}
                  onClick={() => {
                    if (activeView !== tab.key) {
                      setActiveView(tab.key)
                    }
                  }}
                  role="tab"
                  type="button"
                >
                  {tab.label}
                </button>
              ))}
            </div>
            <div className="admin-community-filters" aria-label="Community game filters">
              <label className="admin-community-filters__search">
                <span className="admin-community-sr-only">Search</span>
                <Search aria-hidden="true" />
                <input
                  aria-label="Search by title, venue, host, or city"
                  maxLength={SEARCH_MAX_LENGTH}
                  placeholder="Search title, venue, host, or city..."
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                />
                {searchInput && (
                  <button aria-label="Clear search" type="button" onClick={() => setSearchInput('')}>
                    <X aria-hidden="true" />
                  </button>
                )}
              </label>
            </div>

            <div className="admin-community-count-row">
              <span>{loadState === 'ready' ? countLabel : 'Loading games'}</span>
            </div>

            {pageError && (
              <FormErrorMessage className="admin-community-page-error">
                {pageError}
              </FormErrorMessage>
            )}
            {loadState === 'loading' ? (
              <AdminCommunityGamesLoading />
            ) : loadState === 'ready' ? (
              <>
                <AdminCommunityGamesList games={games} hasFilters={hasFilters} />
                {loadMoreError && (
                  <FormErrorMessage className="admin-community-load-more-error">
                    {loadMoreError}
                  </FormErrorMessage>
                )}
                {hasMoreGames && (
                  <div className="admin-community-load-more">
                    <button
                      className="admin-community-button admin-community-button--load-more"
                      disabled={isLoadingMore}
                      type="button"
                      onClick={loadMoreGames}
                    >
                      {isLoadingMore ? 'Loading...' : 'Load more'}
                    </button>
                  </div>
                )}
              </>
            ) : null}
          </section>
        </div>
      </AdminWorkspaceLayout>
    </>
  )
}

export default AdminCommunityGamesPage
