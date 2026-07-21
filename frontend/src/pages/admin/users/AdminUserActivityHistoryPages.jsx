import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  CalendarDays,
  ClipboardList,
  UserRound,
} from 'lucide-react'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminUsers.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import {
  getAdminUserGameActivity,
  getAdminUserNeedASubActivity,
} from '../shared/adminApi.js'
import {
  formatAdminUserDateTime,
  formatAdminUserStatus,
} from './adminUserFormatters.js'

const PAGE_SIZE = 25

function formatActivityLocation(item) {
  const name = item.venue_name_snapshot || item.location_name || ''
  const location = [
    item.city_snapshot || item.city,
    item.state_snapshot || item.state,
  ].filter(Boolean).join(', ')

  return [name, location].filter(Boolean).join(' · ') || 'Location unavailable'
}

function getGameTargetPath(item) {
  if (item.game_type === 'official') {
    return `/admin/official-games/${item.game_id}`
  }
  if (item.game_type === 'community') {
    return `/admin/community-games/${item.game_id}`
  }
  return ''
}

function getNeedASubTargetPath(item) {
  if (item.activity_type === 'requested' && item.request_id) {
    return `/admin/need-a-sub/requests/${item.request_id}`
  }
  return `/admin/need-a-sub/${item.post_id}`
}

function ActivityHistoryRow({ facts, targetPath }) {
  const content = (
    <div className={`admin-user-activity-list-row__facts admin-user-activity-list-row__facts--${facts.length}`}>
      {facts.map((fact) => (
        <div className="admin-user-activity-fact" key={fact.label}>
          <span>{fact.label}</span>
          <strong>{fact.value}</strong>
        </div>
      ))}
    </div>
  )

  if (!targetPath) {
    return <div className="admin-user-activity-list-row">{content}</div>
  }

  return (
    <Link className="admin-user-activity-list-row" to={targetPath}>
      {content}
    </Link>
  )
}

function ActivityHistoryLoading() {
  return (
    <div className="admin-user-detail-loading" role="status" aria-label="Loading activity">
      {Array.from({ length: 5 }).map((_, index) => (
        <section key={index}>
          <SkeletonBlock height="0.9rem" rounded width="24%" />
          <SkeletonBlock height="3.8rem" rounded width="100%" />
        </section>
      ))}
    </div>
  )
}

function AdminUserActivityHistoryPage({
  description,
  emptyMessage,
  fetchActivity,
  getFacts,
  getTargetPath,
  icon,
  title,
}) {
  const { userId } = useParams()
  const { currentUser } = useAuth()
  const [items, setItems] = useState([])
  const [pageState, setPageState] = useState({
    hasMore: false,
    totalItems: 0,
  })
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')

  const loadActivity = useCallback(async ({ append, offset }) => {
    if (!currentUser || !userId) {
      return
    }

    setLoadState(append ? 'loadingMore' : 'loading')
    setPageError('')

    try {
      const nextActivity = await fetchActivity({
        firebaseUser: currentUser,
        limit: PAGE_SIZE,
        offset,
        userId,
      })

      setItems((currentItems) => (
        append
          ? [...currentItems, ...(nextActivity.items ?? [])]
          : nextActivity.items ?? []
      ))
      setPageState({
        hasMore: Boolean(nextActivity.has_more),
        totalItems: nextActivity.total_items ?? 0,
      })
      setLoadState('ready')
    } catch (error) {
      setPageError(error.message || 'Activity could not be loaded.')
      setLoadState('error')
    }
  }, [currentUser, fetchActivity, userId])

  useEffect(() => {
    let isActive = true

    Promise.resolve().then(() => {
      if (isActive) {
        loadActivity({ append: false, offset: 0 })
      }
    })

    return () => {
      isActive = false
    }
  }, [loadActivity])

  return (
    <AdminWorkspaceLayout
      actions={(
        <div className="admin-user-header-actions">
          <Link className="admin-users-button" to={`/admin/users/${userId}`}>Back</Link>
        </div>
      )}
      breadcrumbs={['Admin', 'People', 'User Directory']}
      description={description}
      icon={icon}
      title={title}
    >
      {pageError && (
        <div className="admin-users-alert" role="alert">
          {pageError}
        </div>
      )}

      {loadState === 'loading' && <ActivityHistoryLoading />}

      {loadState !== 'loading' && (
        <div className="admin-user-history-page">
          <div className="admin-user-history-page__summary">
            <UserRound />
            <span>{pageState.totalItems} total</span>
          </div>

          {items.length === 0 ? (
            <p className="admin-user-detail-empty">{emptyMessage}</p>
          ) : (
            <div className="admin-user-activity-list">
              {items.map((item) => (
                <ActivityHistoryRow
                  facts={getFacts(item)}
                  key={`${item.game_id || item.post_id}-${item.request_id || item.activity_type}`}
                  targetPath={getTargetPath(item)}
                />
              ))}
            </div>
          )}

          {pageState.hasMore && (
            <div className="admin-user-history-page__footer">
              <button
                className="admin-users-button"
                type="button"
                disabled={loadState === 'loadingMore'}
                onClick={() => loadActivity({ append: true, offset: items.length })}
              >
                {loadState === 'loadingMore' ? 'Loading...' : 'Load more'}
              </button>
            </div>
          )}
        </div>
      )}
    </AdminWorkspaceLayout>
  )
}

export function AdminUserGameActivityPage() {
  return (
    <AdminUserActivityHistoryPage
      description="Review the full game outcome history tied to this user."
      emptyMessage="No game activity found for this user."
      fetchActivity={getAdminUserGameActivity}
      getFacts={(item) => [
        {
          label: 'Location',
          value: formatActivityLocation(item),
        },
        {
          label: 'Date',
          value: `${formatAdminUserDateTime(item.scheduled_at)} · ${formatAdminUserStatus(item.game_type)}`,
        },
        {
          label: 'Role',
          value: formatAdminUserStatus(item.role),
        },
        {
          label: 'Outcome',
          value: formatAdminUserStatus(item.outcome),
        },
      ]}
      getTargetPath={getGameTargetPath}
      icon={CalendarDays}
      title="Game Activity"
    />
  )
}

export function AdminUserNeedASubActivityPage() {
  return (
    <AdminUserActivityHistoryPage
      description="Review the full Need a Sub history tied to this user."
      emptyMessage="This user has not created a Need a Sub record or submitted a request."
      fetchActivity={getAdminUserNeedASubActivity}
      getFacts={(item) => {
        const facts = [
          {
            label: 'Location',
            value: formatActivityLocation(item),
          },
          {
            label: 'Date',
            value: formatAdminUserDateTime(item.scheduled_at),
          },
          {
            label: 'Type',
            value: formatAdminUserStatus(item.activity_type),
          },
          {
            label: 'Status',
            value: formatAdminUserStatus(item.status),
          },
        ]
        if (item.activity_type === 'created' && item.subs_needed) {
          facts.push({
            label: 'Subs needed',
            value: String(item.subs_needed),
          })
        }
        if (item.activity_type === 'requested' && item.post_status) {
          facts.push({
            label: 'Post status',
            value: formatAdminUserStatus(item.post_status),
          })
        }
        return facts
      }}
      getTargetPath={getNeedASubTargetPath}
      icon={ClipboardList}
      title="Need a Sub Activity"
    />
  )
}
