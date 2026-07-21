import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  CalendarDays,
  ClipboardList,
  FileClock,
  ShieldBan,
  ShieldCheck,
  ShieldOff,
  Trash2,
  Trophy,
  UserRound,
} from 'lucide-react'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminUsers.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { getAdminUser } from '../shared/adminApi.js'
import { useAdminAccess } from '../shared/useAdminAccess.js'
import {
  formatAdminUserDate,
  formatAdminUserDateTime,
  formatAdminUserStatus,
  shortAdminUserId,
} from './adminUserFormatters.js'
import AdminUserDeletePreviewModal from './AdminUserDeletePreviewModal.jsx'
import AdminUserHostingRestorationModal from './AdminUserHostingRestorationModal.jsx'
import AdminUserHostingRestrictionModal from './AdminUserHostingRestrictionModal.jsx'
import AdminUserSuspensionModal from './AdminUserSuspensionModal.jsx'
import AdminUserUnsuspensionModal from './AdminUserUnsuspensionModal.jsx'

function AdminUserSection({ actions = null, children, icon: Icon, title }) {
  return (
    <section className="admin-user-detail-panel">
      <div className="admin-user-detail-panel__heading">
        <div>
          <Icon />
          <h2>{title}</h2>
        </div>
        {actions}
      </div>
      {children}
    </section>
  )
}

function AdminUserFact({ className = '', label, value }) {
  return (
    <div className={`admin-user-fact ${className}`.trim()}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function AdminUserEmpty({ children }) {
  return <p className="admin-user-detail-empty">{children}</p>
}

function formatDeletionState(user) {
  if (user.deleted_at || user.account_status === 'deleted') {
    return user.deleted_at
      ? `Deleted ${formatAdminUserDate(user.deleted_at)}`
      : 'Deleted'
  }
  if (user.account_status === 'pending_deletion') {
    return 'Pending deletion'
  }
  return 'Not deleted'
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
      <div className="admin-user-fact-grid">
        <AdminUserFact
          className="admin-user-fact--identity"
          label="Full name"
          value={user.display_name || 'No name'}
        />
        <AdminUserFact
          className="admin-user-fact--identity"
          label="Email"
          value={user.email || 'No email'}
        />
        <AdminUserFact
          label="Email status"
          value={user.email_verified ? 'Verified' : 'Unverified'}
        />
        <AdminUserFact label="Role" value={formatAdminUserStatus(user.role)} />
        <AdminUserFact
          label="Member since"
          value={formatAdminUserDate(user.member_since)}
        />
        <AdminUserFact label="User ID" value={shortAdminUserId(user.id)} />
      </div>
    </AdminUserSection>
  )
}

function UserAccountState({ user }) {
  return (
    <AdminUserSection icon={ShieldOff} title="Account State">
      <div className="admin-user-fact-grid admin-user-fact-grid--account-state">
        <AdminUserFact
          label="Account status"
          value={formatAdminUserStatus(user.account_status)}
        />
        <AdminUserFact
          label="Hosting status"
          value={formatAdminUserStatus(user.hosting_status)}
        />
        <AdminUserFact
          label="Deletion status"
          value={formatDeletionState(user)}
        />
      </div>
    </AdminUserSection>
  )
}

function getAccountAction({ canMutateCurrentAccount, canSuspendUsers, user }) {
  if (!canSuspendUsers || !canMutateCurrentAccount) {
    return null
  }

  if (user.account_status === 'suspended') {
    return {
      disabled: false,
      Icon: ShieldCheck,
      label: 'Unsuspend account',
      modal: 'unsuspend',
      variant: 'admin-users-button--success',
    }
  }

  if (user.account_status === 'active') {
    return {
      disabled: false,
      Icon: ShieldBan,
      label: 'Suspend account',
      modal: 'suspend',
      variant: 'admin-users-button--danger',
    }
  }

  return null
}

function getHostingAction({ canManageHosting, canMutateCurrentAccount, user }) {
  if (!canManageHosting || !canMutateCurrentAccount) {
    return null
  }

  if (user.hosting_status === 'restricted') {
    return {
      disabled: false,
      Icon: ShieldCheck,
      label: 'Restore hosting',
      modal: 'restoreHosting',
      variant: 'admin-users-button--success',
    }
  }

  if (user.hosting_status === 'eligible') {
    return {
      disabled: false,
      Icon: ShieldOff,
      label: 'Restrict hosting',
      modal: 'restrictHosting',
      variant: 'admin-users-button--danger',
    }
  }

  return null
}

function AdminUserActionButton({
  action,
  className = '',
  onOpenModal,
}) {
  const Icon = action.Icon
  return (
    <button
      className={[
        'admin-users-button',
        action.variant,
        className,
      ].filter(Boolean).join(' ')}
      type="button"
      onClick={() => {
        if (action.modal) {
          onOpenModal(action.modal)
        }
      }}
    >
      <Icon />
      {action.label}
    </button>
  )
}

function UserActions({
  canDeleteUsers,
  canManageHosting,
  canMutateCurrentAccount,
  canSuspendUsers,
  onOpenModal,
  user,
}) {
  const accountAction = getAccountAction({
    canMutateCurrentAccount,
    canSuspendUsers,
    user,
  })
  const hostingAction = getHostingAction({
    canManageHosting,
    canMutateCurrentAccount,
    user,
  })
  const canDeleteAccount = canDeleteUsers && canMutateCurrentAccount

  if (!accountAction && !hostingAction && !canDeleteAccount) {
    return null
  }

  return (
    <div className="admin-user-action-grid">
      {accountAction && (
        <AdminUserActionButton
          action={accountAction}
          onOpenModal={onOpenModal}
        />
      )}
      {hostingAction && (
        <AdminUserActionButton
          action={hostingAction}
          onOpenModal={onOpenModal}
        />
      )}
      {canDeleteAccount && (
        <button
          className="admin-users-button admin-users-button--danger admin-user-action-button--delete"
          type="button"
          onClick={() => onOpenModal('delete')}
        >
          <Trash2 />
          Delete account
        </button>
      )}
    </div>
  )
}

function UserStats({ stats }) {
  const value = (fieldName) => (
    stats ? String(stats[fieldName]) : 'Unknown'
  )

  return (
    <AdminUserSection icon={Trophy} title="Accountability Summary">
      <div className="admin-user-fact-grid admin-user-fact-grid--accountability">
        <AdminUserFact label="Played" value={value('games_played_count')} />
        <AdminUserFact
          label="Hosted"
          value={value('games_hosted_completed_count')}
        />
        <AdminUserFact label="No shows" value={value('no_show_count')} />
        <AdminUserFact label="Late cancels" value={value('late_cancel_count')} />
        <AdminUserFact label="Host cancels" value={value('host_cancel_count')} />
      </div>
    </AdminUserSection>
  )
}

function formatAdminUserLocation({
  city,
  city_snapshot: citySnapshot,
  location_name: locationName,
  state,
  state_snapshot: stateSnapshot,
  venue_name_snapshot: venueName,
}) {
  const name = venueName || locationName || ''
  const location = [
    citySnapshot || city,
    stateSnapshot || state,
  ].filter(Boolean).join(', ')

  return [name, location].filter(Boolean).join(' · ') || 'Location unavailable'
}

function getGameActivityTargetPath({
  canOpenCommunityGames,
  canOpenOfficialGames,
  item,
}) {
  if (canOpenOfficialGames && item.game_type === 'official') {
    return `/admin/official-games/${item.game_id}`
  }
  if (canOpenCommunityGames && item.game_type === 'community') {
    return `/admin/community-games/${item.game_id}`
  }
  return ''
}

function getNeedASubActivityTargetPath(item) {
  if (item.activity_type === 'requested' && item.request_id) {
    return `/admin/need-a-sub/requests/${item.request_id}`
  }
  return `/admin/need-a-sub/${item.post_id}`
}

function ActivityRow({ facts, targetPath }) {
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

function ActivityViewAllLink({ targetPath }) {
  return <Link className="admin-users-button" to={targetPath}>View all</Link>
}

function GameActivitySection({
  activity,
  canOpenCommunityGames,
  canOpenOfficialGames,
  userId,
}) {
  const items = activity?.items ?? []

  return (
    <AdminUserSection
      actions={(
        <ActivityViewAllLink targetPath={`/admin/users/${userId}/game-activity`} />
      )}
      icon={CalendarDays}
      title="Game Activity"
    >
      {items.length === 0 ? (
        <AdminUserEmpty>No game activity found.</AdminUserEmpty>
      ) : (
        <div className="admin-user-activity-list">
          {items.map((item) => (
            <ActivityRow
              facts={[
                {
                  label: 'Location',
                  value: formatAdminUserLocation(item),
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
              key={item.game_id}
              targetPath={getGameActivityTargetPath({
                canOpenCommunityGames,
                canOpenOfficialGames,
                item,
              })}
            />
          ))}
        </div>
      )}
    </AdminUserSection>
  )
}

function NeedASubSection({ activity, userId }) {
  const items = activity?.items ?? []

  return (
    <AdminUserSection
      actions={(
        <ActivityViewAllLink targetPath={`/admin/users/${userId}/need-a-sub-activity`} />
      )}
      icon={ClipboardList}
      title="Need a Sub Activity"
    >
      {items.length === 0 ? (
        <AdminUserEmpty>This user has not created a Need a Sub record or submitted a request.</AdminUserEmpty>
      ) : (
        <div className="admin-user-activity-list">
          {items.map((item) => {
            const facts = [
              {
                label: 'Location',
                value: formatAdminUserLocation(item),
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

            return (
              <ActivityRow
                facts={facts}
                key={`${item.activity_type}-${item.request_id || item.post_id}`}
                targetPath={getNeedASubActivityTargetPath(item)}
              />
            )
          })}
        </div>
      )}
    </AdminUserSection>
  )
}

function AuditSection({ actionControls = null, actions }) {
  return (
    <AdminUserSection icon={FileClock} title="Admin Actions">
      {actionControls}
      {actions.length === 0 ? (
        <AdminUserEmpty>No admin actions found for this user.</AdminUserEmpty>
      ) : (
        <div className="admin-user-detail-list">
          {actions.map((action) => (
            <div className="admin-user-detail-list__row" key={action.id}>
              <div>
                <strong>{formatAdminUserStatus(action.action_type)}</strong>
                <span>{action.reason || 'No reason recorded.'}</span>
              </div>
              <div>
                <span>Admin {shortAdminUserId(action.admin_user_id)}</span>
              </div>
              <div>
                <span>{formatAdminUserDateTime(action.created_at)}</span>
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
  const {
    hasAdminAccess,
    reload: reloadAdminAccess,
  } = useAdminAccess()
  const [detail, setDetail] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)
  const [isDeletePreviewModalOpen, setIsDeletePreviewModalOpen] = useState(false)
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
  const canOpenOfficialGames = hasAdminAccess
  const canOpenCommunityGames = hasAdminAccess
  const canSuspendUsers = hasAdminAccess
  const canManageHosting = hasAdminAccess
  const canDeleteUsers = hasAdminAccess
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
        || nextAppUser?.role !== 'admin'
      ) {
        navigate('/admin/sign-in', { replace: true })
        return
      }

      reloadAdminAccess()
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

  function handleOpenActionModal(modalName) {
    if (modalName === 'delete') {
      setIsDeletePreviewModalOpen(true)
      return
    }
    if (modalName === 'restrictHosting') {
      setIsHostingRestrictionModalOpen(true)
      return
    }
    if (modalName === 'restoreHosting') {
      setIsHostingRestorationModalOpen(true)
      return
    }
    if (modalName === 'suspend') {
      setIsSuspensionModalOpen(true)
      return
    }
    if (modalName === 'unsuspend') {
      setIsUnsuspensionModalOpen(true)
    }
  }

  return (
    <>
      <AdminWorkspaceLayout
        actions={(
          <div className="admin-user-header-actions">
            <Link className="admin-users-button" to="/admin/users">Back</Link>
          </div>
        )}
        breadcrumbs={['Admin', 'People', 'User Directory']}
        description="Review account state, activity, hosting, and support context."
        headerClassName="admin-user-page-header"
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
            <UserAccountState user={detail.user} />
            <UserStats stats={detail.stats} />
            <GameActivitySection
              activity={detail.game_activity}
              canOpenCommunityGames={canOpenCommunityGames}
              canOpenOfficialGames={canOpenOfficialGames}
              userId={detail.user.id}
            />
            <NeedASubSection
              activity={detail.need_a_sub_activity}
              userId={detail.user.id}
            />
            <AuditSection
              actionControls={(
                <UserActions
                  canDeleteUsers={canDeleteUsers}
                  canManageHosting={canManageHosting}
                  canMutateCurrentAccount={canMutateCurrentAccount}
                  canSuspendUsers={canSuspendUsers}
                  user={detail.user}
                  onOpenModal={handleOpenActionModal}
                />
              )}
              actions={detail.audit_actions ?? []}
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
    </>
  )
}

export default AdminUserPage
