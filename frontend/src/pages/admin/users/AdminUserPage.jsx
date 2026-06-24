import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  CalendarDays,
  ClipboardList,
  FileClock,
  Flag,
  RefreshCw,
  ShieldBan,
  ShieldCheck,
  ShieldOff,
  Trash2,
  Trophy,
  UserCog,
  UserRound,
  WalletCards,
} from 'lucide-react'
import { AppPageShell } from '../../../components/app/index.js'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminUsers.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { getAdminUser } from '../shared/adminApi.js'
import {
  ADMIN_PERMISSIONS,
  hasAdminPermission,
} from '../shared/adminWorkspaceData.js'
import { useAdminAccess } from '../shared/useAdminAccess.js'
import {
  formatAdminUserDate,
  formatAdminUserDateTime,
  formatAdminUserLocation,
  formatAdminUserStatus,
  shortAdminUserId,
} from './adminUserFormatters.js'
import AdminUserDeletePreviewModal from './AdminUserDeletePreviewModal.jsx'
import AdminUserHostingRestorationModal from './AdminUserHostingRestorationModal.jsx'
import AdminUserHostingRestrictionModal from './AdminUserHostingRestrictionModal.jsx'
import AdminUserStaffRoleModal from './AdminUserStaffRoleModal.jsx'
import AdminUserSuspensionModal from './AdminUserSuspensionModal.jsx'
import AdminUserUnsuspensionModal from './AdminUserUnsuspensionModal.jsx'

function AdminUserSection({ children, count, icon: Icon, title }) {
  return (
    <section className="admin-user-detail-panel">
      <div className="admin-user-detail-panel__heading">
        <div>
          <Icon />
          <h2>{title}</h2>
        </div>
        {count !== undefined && <span>{count}</span>}
      </div>
      {children}
    </section>
  )
}

function AdminUserEmpty({ children }) {
  return <p className="admin-user-detail-empty">{children}</p>
}

function AdminUserLoading() {
  return (
    <div className="admin-user-detail-loading" role="status" aria-label="Loading user">
      <section>
        <SkeletonBlock height="1rem" rounded width="32%" />
        <SkeletonBlock height="4.8rem" rounded width="100%" />
      </section>
      {Array.from({ length: 4 }).map((_, index) => (
        <section key={index}>
          <SkeletonBlock height="0.9rem" rounded width="24%" />
          <SkeletonBlock height="3.8rem" rounded width="100%" />
        </section>
      ))}
    </div>
  )
}

function UserSummary({ user }) {
  return (
    <AdminUserSection icon={UserRound} title="User Summary">
      <div className="admin-user-summary-kpis">
        <div>
          <span>Account</span>
          <strong>{formatAdminUserStatus(user.account_status)}</strong>
        </div>
        <div>
          <span>Role</span>
          <strong>{formatAdminUserStatus(user.role)}</strong>
        </div>
        <div>
          <span>Hosting</span>
          <strong>{formatAdminUserStatus(user.hosting_status)}</strong>
        </div>
        <div>
          <span>Email</span>
          <strong>{user.email_verified ? 'Verified' : 'Unverified'}</strong>
        </div>
      </div>
      <div className="admin-user-detail-fields">
        <div>
          <span>User ID</span>
          <code>{user.id}</code>
        </div>
        <div>
          <span>Email</span>
          <strong>{user.email || 'No email'}</strong>
        </div>
        <div>
          <span>Phone</span>
          <strong>{user.phone || 'No phone'}</strong>
        </div>
        <div>
          <span>Location</span>
          <strong>{formatAdminUserLocation(user)}</strong>
        </div>
        <div>
          <span>Member since</span>
          <strong>{formatAdminUserDate(user.member_since)}</strong>
        </div>
        <div>
          <span>Hosting suspended until</span>
          <strong>{formatAdminUserDateTime(user.hosting_suspended_until)}</strong>
        </div>
        <div>
          <span>Updated</span>
          <strong>{formatAdminUserDateTime(user.updated_at)}</strong>
        </div>
        <div>
          <span>Deleted</span>
          <strong>{formatAdminUserDateTime(user.deleted_at)}</strong>
        </div>
      </div>
    </AdminUserSection>
  )
}

function UserStats({ stats }) {
  return (
    <AdminUserSection icon={Trophy} title="Accountability Summary">
      {!stats ? (
        <AdminUserEmpty>No cached accountability summary found.</AdminUserEmpty>
      ) : (
        <>
          <div className="admin-user-summary-kpis admin-user-summary-kpis--five">
            <div>
              <span>Played</span>
              <strong>{stats.games_played_count}</strong>
            </div>
            <div>
              <span>Hosted</span>
              <strong>{stats.games_hosted_completed_count}</strong>
            </div>
            <div>
              <span>No shows</span>
              <strong>{stats.no_show_count}</strong>
            </div>
            <div>
              <span>Late cancels</span>
              <strong>{stats.late_cancel_count}</strong>
            </div>
            <div>
              <span>Host cancels</span>
              <strong>{stats.host_cancel_count}</strong>
            </div>
          </div>
          <p className="admin-user-detail-note">
            Cached summary, calculated {formatAdminUserDateTime(stats.last_calculated_at)}.
          </p>
        </>
      )}
    </AdminUserSection>
  )
}

function GameRelationshipRow({
  canOpenCommunityGames,
  canOpenOfficialGames,
  item,
  relationship,
}) {
  const title = item.game_title || item.title
  const gameId = item.game_id || item.id
  let targetPath = ''
  if (canOpenOfficialGames && item.game_type === 'official') {
    targetPath = `/admin/official-games/${gameId}`
  }
  if (canOpenCommunityGames && item.game_type === 'community') {
    targetPath = `/admin/community-games/${gameId}`
  }

  return (
    <div className="admin-user-activity-row">
      <div>
        {targetPath ? (
          <Link to={targetPath}>{title}</Link>
        ) : (
          <strong>{title}</strong>
        )}
        <span>{relationship}</span>
      </div>
      <div>
        <span>{formatAdminUserStatus(item.game_status)}</span>
        <span>{formatAdminUserStatus(item.game_type)}</span>
      </div>
      <div>
        <span>{formatAdminUserDateTime(item.starts_at)}</span>
        <code>{shortAdminUserId(gameId)}</code>
      </div>
    </div>
  )
}

function GameActivitySection({
  bookings,
  canOpenCommunityGames,
  canOpenOfficialGames,
  communityGames,
  officialHosts,
  participations,
}) {
  const count = (
    bookings.length
    + participations.length
    + communityGames.length
    + officialHosts.length
  )

  return (
    <AdminUserSection count={count} icon={CalendarDays} title="Game Activity">
      {count === 0 ? (
        <AdminUserEmpty>No game activity found.</AdminUserEmpty>
      ) : (
        <div className="admin-user-activity-groups">
          {bookings.length > 0 && (
            <div>
              <h3>Bookings</h3>
              {bookings.map((booking) => (
                <GameRelationshipRow
                  canOpenCommunityGames={canOpenCommunityGames}
                  canOpenOfficialGames={canOpenOfficialGames}
                  item={booking}
                  key={booking.id}
                  relationship={`${formatAdminUserStatus(booking.booking_status)} · ${booking.participant_count} players`}
                />
              ))}
            </div>
          )}
          {participations.length > 0 && (
            <div>
              <h3>Participation</h3>
              {participations.map((participation) => (
                <GameRelationshipRow
                  canOpenCommunityGames={canOpenCommunityGames}
                  canOpenOfficialGames={canOpenOfficialGames}
                  item={participation}
                  key={participation.id}
                  relationship={`${formatAdminUserStatus(participation.participant_status)} · ${formatAdminUserStatus(participation.attendance_status)}`}
                />
              ))}
            </div>
          )}
          {communityGames.length > 0 && (
            <div>
              <h3>Community Hosting</h3>
              {communityGames.map((game) => (
                <GameRelationshipRow
                  canOpenCommunityGames={canOpenCommunityGames}
                  canOpenOfficialGames={canOpenOfficialGames}
                  item={game}
                  key={game.id}
                  relationship={`${game.city}, ${game.state}`}
                />
              ))}
            </div>
          )}
          {officialHosts.length > 0 && (
            <div>
              <h3>Official Host Assignments</h3>
              {officialHosts.map((game) => (
                <GameRelationshipRow
                  canOpenCommunityGames={canOpenCommunityGames}
                  canOpenOfficialGames={canOpenOfficialGames}
                  item={game}
                  key={game.id}
                  relationship={`${game.city}, ${game.state}`}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </AdminUserSection>
  )
}

function NeedASubSection({ posts, requests }) {
  const count = posts.length + requests.length

  return (
    <AdminUserSection count={count} icon={ClipboardList} title="Need a Sub Activity">
      {count === 0 ? (
        <AdminUserEmpty>No Need a Sub activity found.</AdminUserEmpty>
      ) : (
        <div className="admin-user-activity-groups">
          {posts.length > 0 && (
            <div>
              <h3>Posts Owned</h3>
              {posts.map((post) => (
                <div className="admin-user-activity-row" key={post.id}>
                  <div>
                    <strong>{post.team_name || 'Need a Sub post'}</strong>
                    <span>{post.city}, {post.state}</span>
                  </div>
                  <div>
                    <span>{formatAdminUserStatus(post.post_status)}</span>
                    <span>{post.subs_needed} subs needed</span>
                  </div>
                  <div>
                    <span>{formatAdminUserDateTime(post.starts_at)}</span>
                    <code>{shortAdminUserId(post.id)}</code>
                  </div>
                </div>
              ))}
            </div>
          )}
          {requests.length > 0 && (
            <div>
              <h3>Requests Made</h3>
              {requests.map((request) => (
                <div className="admin-user-activity-row" key={request.id}>
                  <div>
                    <strong>{request.team_name || 'Need a Sub request'}</strong>
                    <span>{request.city}, {request.state}</span>
                  </div>
                  <div>
                    <span>{formatAdminUserStatus(request.request_status)}</span>
                    <span>Post {formatAdminUserStatus(request.post_status)}</span>
                  </div>
                  <div>
                    <span>{formatAdminUserDateTime(request.starts_at)}</span>
                    <code>{shortAdminUserId(request.id)}</code>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </AdminUserSection>
  )
}

function SupportFlagsSection({ flags }) {
  return (
    <AdminUserSection count={flags.length} icon={Flag} title="Support Flags">
      {flags.length === 0 ? (
        <AdminUserEmpty>No user-anchored support flags found.</AdminUserEmpty>
      ) : (
        <div className="admin-user-detail-list">
          {flags.map((flag) => (
            <div className="admin-user-detail-list__row" key={flag.id}>
              <div>
                <strong>{flag.title}</strong>
                <span>{flag.summary}</span>
              </div>
              <div>
                <span>{formatAdminUserStatus(flag.flag_status)}</span>
                <span>{formatAdminUserStatus(flag.severity)}</span>
              </div>
              <div>
                <span>{formatAdminUserDateTime(flag.updated_at)}</span>
                <code>{shortAdminUserId(flag.id)}</code>
              </div>
            </div>
          ))}
        </div>
      )}
    </AdminUserSection>
  )
}

function AuditSection({ actions, canViewAudit }) {
  return (
    <AdminUserSection count={actions.length} icon={FileClock} title="Audit History">
      {!canViewAudit ? (
        <AdminUserEmpty>Audit history is not available for this staff account.</AdminUserEmpty>
      ) : actions.length === 0 ? (
        <AdminUserEmpty>No directly user-targeted audit actions found.</AdminUserEmpty>
      ) : (
        <div className="admin-user-detail-list">
          {actions.map((action) => (
            <div className="admin-user-detail-list__row" key={action.id}>
              <div>
                <strong>{formatAdminUserStatus(action.action_type)}</strong>
                <span>{action.reason || 'No reason recorded.'}</span>
              </div>
              <div>
                <span>Staff {shortAdminUserId(action.admin_user_id)}</span>
              </div>
              <div>
                <span>{formatAdminUserDateTime(action.created_at)}</span>
                <code>{shortAdminUserId(action.id)}</code>
              </div>
            </div>
          ))}
        </div>
      )}
    </AdminUserSection>
  )
}

function AdminUserPage() {
  const { userId } = useParams()
  const navigate = useNavigate()
  const {
    appUser,
    currentUser,
    logout,
    syncCurrentFirebaseUser,
  } = useAuth()
  const { adminAccess } = useAdminAccess()
  const [detail, setDetail] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)
  const [isDeletePreviewModalOpen, setIsDeletePreviewModalOpen] = useState(false)
  const [isStaffRoleModalOpen, setIsStaffRoleModalOpen] = useState(false)
  const [isHostingRestorationModalOpen, setIsHostingRestorationModalOpen] = useState(false)
  const [isHostingRestrictionModalOpen, setIsHostingRestrictionModalOpen] = useState(false)
  const [isSuspensionModalOpen, setIsSuspensionModalOpen] = useState(false)
  const [isUnsuspensionModalOpen, setIsUnsuspensionModalOpen] = useState(false)

  useEffect(() => {
    let isMounted = true

    async function loadUser() {
      if (!currentUser || !userId) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const nextDetail = await getAdminUser({
          firebaseUser: currentUser,
          userId,
        })

        if (!isMounted) {
          return
        }

        setDetail(nextDetail)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setDetail(null)
        setPageError(error.message || 'User support detail could not be loaded.')
        setLoadState('error')
      }
    }

    loadUser()

    return () => {
      isMounted = false
    }
  }, [currentUser, refreshCount, userId])

  const pageTitle = useMemo(
    () => detail?.user?.display_name || 'User Support',
    [detail],
  )
  const canOpenOfficialGames = hasAdminPermission(
    adminAccess,
    ADMIN_PERMISSIONS.OFFICIAL_GAMES_READ,
  )
  const canOpenCommunityGames = hasAdminPermission(
    adminAccess,
    ADMIN_PERMISSIONS.COMMUNITY_GAMES_READ,
  )
  const canSuspendUsers = hasAdminPermission(
    adminAccess,
    ADMIN_PERMISSIONS.USERS_SUSPEND,
  )
  const canManageHosting = hasAdminPermission(
    adminAccess,
    ADMIN_PERMISSIONS.USERS_HOSTING_MANAGE,
  )
  const canManageStaff = hasAdminPermission(
    adminAccess,
    ADMIN_PERMISSIONS.STAFF_MANAGE,
  )
  const canDeleteUsers = hasAdminPermission(
    adminAccess,
    ADMIN_PERMISSIONS.USERS_DELETE,
  )
  const canMutateCurrentAccount = (
    Boolean(detail?.user)
    && detail?.user?.account_status !== 'deleted'
    && detail?.user?.account_status !== 'pending_deletion'
  )
  const isViewingCurrentAppUser = (
    Boolean(appUser?.id)
    && detail?.user?.id === appUser?.id
  )

  async function refreshSelfAdminAccess() {
    if (!isViewingCurrentAppUser) {
      setRefreshCount((count) => count + 1)
      return
    }

    try {
      const nextAppUser = await syncCurrentFirebaseUser()
      if (
        nextAppUser?.account_status !== 'active'
        || !['admin', 'moderator'].includes(nextAppUser?.role)
      ) {
        navigate('/admin/sign-in', { replace: true })
        return
      }
    } catch {
      navigate('/admin/sign-in', { replace: true })
      return
    }

    setRefreshCount((count) => count + 1)
  }

  function handleUserDeleted() {
    if (isViewingCurrentAppUser) {
      logout()
        .catch(() => {})
        .finally(() => {
          navigate('/', { replace: true })
        })
      return
    }

    setRefreshCount((count) => count + 1)
  }

  return (
    <AppPageShell className="admin-page" mainClassName="admin-shell">
      <AdminWorkspaceLayout
        actions={(
          <div className="admin-user-header-actions">
            <Link className="admin-users-button" to="/admin/users">Back</Link>
            {canSuspendUsers && detail?.user?.account_status === 'active' && (
              <button
                className="admin-users-button admin-users-button--danger"
                type="button"
                onClick={() => setIsSuspensionModalOpen(true)}
              >
                <ShieldBan />
                Suspend
              </button>
            )}
            {canSuspendUsers && detail?.user?.account_status === 'suspended' && (
              <button
                className="admin-users-button admin-users-button--success"
                type="button"
                onClick={() => setIsUnsuspensionModalOpen(true)}
              >
                <ShieldCheck />
                Unsuspend
              </button>
            )}
            {canManageHosting
              && canMutateCurrentAccount
              && detail?.user?.hosting_status === 'eligible' && (
              <button
                className="admin-users-button admin-users-button--danger"
                type="button"
                onClick={() => setIsHostingRestrictionModalOpen(true)}
              >
                <ShieldOff />
                Restrict hosting
              </button>
            )}
            {canManageHosting
              && canMutateCurrentAccount
              && detail?.user?.hosting_status === 'restricted' && (
              <button
                className="admin-users-button admin-users-button--success"
                type="button"
                onClick={() => setIsHostingRestorationModalOpen(true)}
              >
                <ShieldCheck />
                Restore hosting
              </button>
            )}
            {canManageStaff && canMutateCurrentAccount && (
              <button
                className="admin-users-button"
                type="button"
                onClick={() => setIsStaffRoleModalOpen(true)}
              >
                <UserCog />
                Change role
              </button>
            )}
            {canDeleteUsers && canMutateCurrentAccount && (
              <button
                className="admin-users-button admin-users-button--danger"
                type="button"
                onClick={() => setIsDeletePreviewModalOpen(true)}
              >
                <Trash2 />
                Delete account
              </button>
            )}
            {detail?.capabilities?.can_view_money && (
              <Link className="admin-users-button" to={`/admin/money/users/${userId}`}>
                <WalletCards />
                Money Support
              </Link>
            )}
            <button
              className="admin-users-button admin-users-button--icon"
              aria-label="Refresh user"
              title="Refresh user"
              type="button"
              onClick={() => setRefreshCount((count) => count + 1)}
            >
              <RefreshCw />
            </button>
          </div>
        )}
        breadcrumbs={['Admin', 'People', 'Users']}
        description="Review account state, activity, hosting, staff, and support context."
        icon={UserRound}
        title={pageTitle}
      >
        {pageError && (
          <div className="admin-users-alert" role="alert">
            {pageError}
          </div>
        )}

        {loadState === 'loading' && <AdminUserLoading />}

        {loadState === 'ready' && detail && (
          <div className="admin-user-detail-layout">
            <UserSummary user={detail.user} />
            <UserStats stats={detail.stats} />
            <GameActivitySection
              bookings={detail.bookings ?? []}
              canOpenCommunityGames={canOpenCommunityGames}
              canOpenOfficialGames={canOpenOfficialGames}
              communityGames={detail.community_games_hosted ?? []}
              officialHosts={detail.official_host_assignments ?? []}
              participations={detail.participations ?? []}
            />
            <NeedASubSection
              posts={detail.sub_posts_owned ?? []}
              requests={detail.sub_requests_made ?? []}
            />
            <SupportFlagsSection flags={detail.support_flags ?? []} />
            <AuditSection
              actions={detail.audit_actions ?? []}
              canViewAudit={detail.capabilities?.can_view_audit}
            />
          </div>
        )}
      </AdminWorkspaceLayout>

      {isSuspensionModalOpen && detail?.user && (
        <AdminUserSuspensionModal
          canOpenOfficialGames={canOpenOfficialGames}
          firebaseUser={currentUser}
          user={detail.user}
          onClose={() => setIsSuspensionModalOpen(false)}
          onSuspended={refreshSelfAdminAccess}
        />
      )}
      {isDeletePreviewModalOpen && detail?.user && (
        <AdminUserDeletePreviewModal
          canOpenOfficialGames={canOpenOfficialGames}
          firebaseUser={currentUser}
          user={detail.user}
          onClose={() => setIsDeletePreviewModalOpen(false)}
          onDeleted={handleUserDeleted}
        />
      )}
      {isStaffRoleModalOpen && detail?.user && (
        <AdminUserStaffRoleModal
          firebaseUser={currentUser}
          user={detail.user}
          onChanged={refreshSelfAdminAccess}
          onClose={() => setIsStaffRoleModalOpen(false)}
        />
      )}
      {isHostingRestrictionModalOpen && detail?.user && (
        <AdminUserHostingRestrictionModal
          firebaseUser={currentUser}
          user={detail.user}
          onClose={() => setIsHostingRestrictionModalOpen(false)}
          onRestricted={() => setRefreshCount((count) => count + 1)}
        />
      )}
      {isHostingRestorationModalOpen && detail?.user && (
        <AdminUserHostingRestorationModal
          firebaseUser={currentUser}
          user={detail.user}
          onClose={() => setIsHostingRestorationModalOpen(false)}
          onRestored={() => setRefreshCount((count) => count + 1)}
        />
      )}
      {isUnsuspensionModalOpen && detail?.user && (
        <AdminUserUnsuspensionModal
          firebaseUser={currentUser}
          user={detail.user}
          onClose={() => setIsUnsuspensionModalOpen(false)}
          onUnsuspended={() => setRefreshCount((count) => count + 1)}
        />
      )}
    </AppPageShell>
  )
}

export default AdminUserPage
