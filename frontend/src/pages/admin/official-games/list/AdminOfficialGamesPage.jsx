import { useEffect, useMemo, useRef, useState } from 'react'
import { Search, Trophy, X } from 'lucide-react'
import { FormErrorMessage } from '../../../../components/FormErrorMessage.jsx'
import { GameDateIcon } from '../../../../components/GameFactIcons.jsx'
import { SkeletonBlock } from '../../../../components/skeleton/index.js'
import { useAuth } from '../../../../hooks/useAuth.js'
import '../../../../styles/admin/AdminOfficialGames.css'
import AdminWorkspaceLayout from '../../shared/AdminWorkspaceLayout.jsx'
import AdminOfficialGamesList from './AdminOfficialGamesList.jsx'
import { listAdminOfficialGames } from '../shared/adminOfficialGamesApi.js'

const OFFICIAL_GAMES_LIST_LIMIT = 24
const SEARCH_DEBOUNCE_MS = 300
const SEARCH_MIN_LENGTH = 3
const SEARCH_MAX_LENGTH = 120

const officialGameViewTabs = [
  { key: 'active', label: 'Active' },
  { key: 'full', label: 'Full' },
  { key: 'completed', label: 'Completed' },
  { key: 'cancelled', label: 'Cancelled' },
  { key: 'expired', label: 'Expired' },
  { key: 'removed', label: 'Removed' },
]

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

function AdminOfficialGamesListSkeleton() {
  return (
    <div className="admin-official-date-groups admin-official-date-groups--skeleton" aria-hidden="true">
      <section className="admin-official-date-group">
        <div className="admin-official-date-group__header">
          <SkeletonBlock height="1rem" rounded width="12rem" />
          <SkeletonBlock height="0.8rem" rounded width="4.2rem" />
        </div>
        <div className="admin-official-card-grid">
          {Array.from({ length: OFFICIAL_GAMES_LIST_LIMIT }, (_, item) => (
            <article className="admin-official-game-card admin-official-game-card--skeleton" key={item}>
              <div className="admin-official-game-card__thumb admin-official-game-card__thumb--skeleton">
                <SkeletonBlock className="admin-official-game-card__thumb-skeleton" height="100%" width="100%" />
              </div>
              <div className="admin-official-game-card__body">
                <SkeletonBlock height="1rem" rounded width="82%" />
                <SkeletonBlock height="0.78rem" rounded width="64%" />
                <SkeletonBlock height="0.78rem" rounded width="72%" />
                <SkeletonBlock height="0.78rem" rounded width="58%" />
              </div>
              <div className="admin-official-game-card__footer">
                <SkeletonBlock height="0.84rem" rounded width="4.8rem" />
                <SkeletonBlock height="0.84rem" rounded width="3.4rem" />
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

function AdminOfficialGamesPage() {
  const { currentUser } = useAuth()
  const [activeView, setActiveView] = useState('active')
  const [searchInput, setSearchInput] = useState('')
  const [selectedDate, setSelectedDate] = useState('')
  const [games, setGames] = useState([])
  const [nextCursor, setNextCursor] = useState(null)
  const [hasMore, setHasMore] = useState(false)
  const [loadState, setLoadState] = useState('loading')
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [pageError, setPageError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const dateInputRef = useRef(null)
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
    const loadTimer = window.setTimeout(() => {
      if (!isMounted || requestId !== requestIdRef.current) {
        return
      }

      setLoadState('loading')
      setIsLoadingMore(false)
      setPageError('')
      setGames([])
      setNextCursor(null)
      setHasMore(false)

      listAdminOfficialGames({
        firebaseUser: currentUser,
        limit: OFFICIAL_GAMES_LIST_LIMIT,
        search: activeSearch,
        startsOn: selectedDate,
        view: activeView,
      })
        .then((gameResponse) => {
          if (!isMounted || requestId !== requestIdRef.current) {
            return
          }

          setGames(gameResponse.games ?? [])
          setNextCursor(gameResponse.next_cursor ?? null)
          setHasMore(Boolean(gameResponse.has_more))
          setLoadState('ready')
        })
        .catch((error) => {
          if (!isMounted || requestId !== requestIdRef.current) {
            return
          }

          setPageError(error.message || 'Official games could not be loaded.')
          setLoadState('error')
        })
    }, 0)

    return () => {
      isMounted = false
      window.clearTimeout(loadTimer)
    }
  }, [activeSearch, activeView, currentUser, refreshKey, selectedDate])

  const hasFilters = Boolean(activeSearch || selectedDate)
  const gameCountLabel = useMemo(() => {
    const count = games.length
    return `${count} ${count === 1 ? 'game' : 'games'}`
  }, [games.length])

  function prepareFreshLoad() {
    requestIdRef.current += 1
    setLoadState('loading')
    setIsLoadingMore(false)
    setPageError('')
    setGames([])
    setNextCursor(null)
    setHasMore(false)
  }

  function retryList() {
    prepareFreshLoad()
    setRefreshKey((currentValue) => currentValue + 1)
  }

  function clearSearch() {
    setSearchInput('')
  }

  function openDatePicker() {
    const dateInput = dateInputRef.current

    if (!dateInput) {
      return
    }

    if (typeof dateInput.showPicker === 'function') {
      dateInput.showPicker()
      return
    }

    dateInput.focus()
  }

  function loadMoreGames() {
    if (!hasMore || !nextCursor || isLoadingMore) {
      return
    }

    setIsLoadingMore(true)
    setPageError('')
    const requestId = requestIdRef.current

    listAdminOfficialGames({
      cursor: nextCursor,
      firebaseUser: currentUser,
      limit: OFFICIAL_GAMES_LIST_LIMIT,
      search: activeSearch,
      startsOn: selectedDate,
      view: activeView,
    })
      .then((gameResponse) => {
        if (requestId !== requestIdRef.current) {
          return
        }

        setGames((currentGames) => [
          ...currentGames,
          ...(gameResponse.games ?? []),
        ])
        setNextCursor(gameResponse.next_cursor ?? null)
        setHasMore(Boolean(gameResponse.has_more))
      })
      .catch((error) => {
        if (requestId !== requestIdRef.current) {
          return
        }

        setPageError(error.message || 'More official games could not be loaded.')
      })
      .finally(() => {
        if (requestId !== requestIdRef.current) {
          return
        }

        setIsLoadingMore(false)
      })
  }

  return (
    <AdminWorkspaceLayout
      breadcrumbs={['Admin', 'Games', 'Official Games']}
      description="Find and manage Pickup Lane official games."
      icon={Trophy}
      title="Official Games"
    >
      <section className="admin-official-panel admin-official-panel--list" aria-label="Official games list">
        <div className="admin-official-view-tabs" aria-label="Official game views" role="tablist">
          {officialGameViewTabs.map((tab) => (
            <button
              aria-selected={activeView === tab.key}
              className={activeView === tab.key ? 'is-active' : ''}
              key={tab.key}
              onClick={() => {
                if (activeView !== tab.key) {
                  prepareFreshLoad()
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

        <div className="admin-official-toolbar" aria-label="Official game filters">
          <label className="admin-official-search-field">
            <span className="admin-official-sr-only">Search games</span>
            <Search aria-hidden="true" />
            <input
              onChange={(event) => {
                setSearchInput(event.target.value)
              }}
              maxLength={SEARCH_MAX_LENGTH}
              placeholder="Search title, venue, city, or state..."
              type="text"
              value={searchInput}
            />
            {searchInput && (
              <button aria-label="Clear search" onClick={clearSearch} type="button">
                <X aria-hidden="true" />
              </button>
            )}
          </label>

          <div className="admin-official-date-field">
            <span className="admin-official-sr-only">Filter by date</span>
            <input
              aria-label="Filter by date"
              className={selectedDate ? '' : 'is-empty'}
              onChange={(event) => {
                prepareFreshLoad()
                setSelectedDate(event.target.value)
              }}
              ref={dateInputRef}
              type="date"
              value={selectedDate}
            />
            <button aria-label="Open date picker" onClick={openDatePicker} type="button">
              <GameDateIcon aria-hidden="true" />
            </button>
          </div>
        </div>

        <div className="admin-official-count-row">
          <span>{gameCountLabel}</span>
        </div>

        {pageError && (
          <div className="admin-official-error-row">
            <FormErrorMessage className="admin-official-page-error">
              {pageError}
            </FormErrorMessage>
            <button type="button" onClick={retryList}>
              Retry
            </button>
          </div>
        )}

        {loadState === 'loading' && <AdminOfficialGamesListSkeleton />}

        {loadState === 'ready' && (
          <>
            <AdminOfficialGamesList games={games} hasFilters={hasFilters} />
            {hasMore && (
              <div className="admin-official-load-more">
                <button
                  disabled={isLoadingMore}
                  onClick={loadMoreGames}
                  type="button"
                >
                  {isLoadingMore ? 'Loading...' : 'Load more'}
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </AdminWorkspaceLayout>
  )
}

export default AdminOfficialGamesPage
