import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  CreditCard,
  EyeOff,
  FileText,
  FileClock,
  Flag,
  RefreshCw,
  Settings2,
  ShieldAlert,
  UsersRound,
  WalletCards,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminCommunityGames.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { getAdminCommunityGame } from '../shared/adminApi.js'
import {
  formatAdminCommunityDateTime,
  formatAdminCommunityBoolean,
  formatAdminCommunityMoney,
  formatAdminCommunityStatus,
  shortAdminCommunityId,
} from './adminCommunityGameFormatters.js'
import AdminCommunityGameHidePaymentTextModal from './AdminCommunityGameHidePaymentTextModal.jsx'
import AdminCommunityGameReviewModal from './AdminCommunityGameReviewModal.jsx'

const DETAIL_PAGE_SIZE = 50

function AdminCommunitySection({ children, count, icon: Icon, title }) {
  return (
    <section className="admin-community-detail-panel">
      <div className="admin-community-detail-panel__heading">
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

function AdminCommunityEmpty({ children }) {
  return <p className="admin-community-empty-line">{children}</p>
}

function CollectionPagination({
  label,
  limit,
  offset,
  onOffsetChange,
  pageLength,
  totalCount,
}) {
  if (totalCount <= limit) return null

  const pageStart = totalCount ? offset + 1 : 0
  const pageEnd = Math.min(offset + pageLength, totalCount)
  return (
    <nav aria-label={`${label} pagination`} className="admin-community-pagination">
      <span>{pageStart}-{pageEnd} of {totalCount}</span>
      <div>
        <button
          aria-label={`Previous ${label} page`}
          className="admin-community-button admin-community-button--icon"
          disabled={offset <= 0}
          title="Previous page"
          type="button"
          onClick={() => onOffsetChange(Math.max(0, offset - limit))}
        >
          <ChevronLeft />
        </button>
        <button
          aria-label={`Next ${label} page`}
          className="admin-community-button admin-community-button--icon"
          disabled={offset + pageLength >= totalCount}
          title="Next page"
          type="button"
          onClick={() => onOffsetChange(offset + limit)}
        >
          <ChevronRight />
        </button>
      </div>
    </nav>
  )
}

function AdminCommunityGameLoading() {
  return (
    <div
      aria-label="Loading community game"
      className="admin-community-detail-loading"
      role="status"
    >
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

function FieldGrid({ fields }) {
  return (
    <div className="admin-community-fields">
      {fields.map((field) => (
        <div key={field.label}>
          <span>{field.label}</span>
          {field.code ? <code>{field.value}</code> : <strong>{field.value}</strong>}
        </div>
      ))}
    </div>
  )
}

function GameSummary({ detail }) {
  const { game, host, moderation_state: moderationState } = detail
  const hostPaymentLabel = moderationState.unsafe_payment_text_hidden
    ? 'Hidden'
    : moderationState.host_payment_snapshot_present
      ? 'Present'
      : 'None'

  return (
    <AdminCommunitySection icon={ShieldAlert} title="Game Summary">
      <div className="admin-community-kpis">
        <div>
          <span>Status</span>
          <strong>{formatAdminCommunityStatus(game.game_status)}</strong>
        </div>
        <div>
          <span>Publish</span>
          <strong>{formatAdminCommunityStatus(game.publish_status)}</strong>
        </div>
        <div>
          <span>Price</span>
          <strong>
            {formatAdminCommunityMoney(game.price_per_player_cents, game.currency)}
          </strong>
        </div>
        <div>
          <span>Host text</span>
          <strong>{hostPaymentLabel}</strong>
        </div>
      </div>
      <FieldGrid
        fields={[
          { label: 'Game ID', value: game.id, code: true },
          { label: 'Host', value: host?.display_name || 'No host' },
          { label: 'Host status', value: formatAdminCommunityStatus(host?.hosting_status) },
          {
            label: 'Starts',
            value: formatAdminCommunityDateTime(game.starts_at, game.timezone),
          },
          {
            label: 'Ends',
            value: formatAdminCommunityDateTime(game.ends_at, game.timezone),
          },
          { label: 'Location', value: `${game.city_snapshot}, ${game.state_snapshot}` },
          { label: 'Venue', value: game.venue_name_snapshot },
          { label: 'Address', value: game.address_snapshot },
          { label: 'Neighborhood', value: game.neighborhood_snapshot || 'None' },
          { label: 'Payment', value: formatAdminCommunityStatus(game.payment_collection_type) },
          { label: 'Timezone', value: game.timezone },
        ]}
      />
    </AdminCommunitySection>
  )
}

function RosterSummary({ summary }) {
  return (
    <AdminCommunitySection icon={UsersRound} title="Roster Summary">
      <div className="admin-community-kpis admin-community-kpis--seven">
        <div>
          <span>Total</span>
          <strong>{summary.total_count}</strong>
        </div>
        <div>
          <span>Confirmed</span>
          <strong>{summary.confirmed_count}</strong>
        </div>
        <div>
          <span>Users</span>
          <strong>{summary.registered_user_count}</strong>
        </div>
        <div>
          <span>Guests</span>
          <strong>{summary.guest_count}</strong>
        </div>
        <div>
          <span>Waitlist</span>
          <strong>{summary.waitlisted_count}</strong>
        </div>
        <div>
          <span>Pending</span>
          <strong>{summary.pending_payment_count}</strong>
        </div>
        <div>
          <span>Inactive</span>
          <strong>{summary.inactive_count}</strong>
        </div>
      </div>
    </AdminCommunitySection>
  )
}

function GameConfiguration({ game }) {
  return (
    <AdminCommunitySection icon={Settings2} title="Game Configuration">
      <FieldGrid
        fields={[
          { label: 'Sport', value: formatAdminCommunityStatus(game.sport_type) },
          { label: 'Format', value: game.format_label },
          { label: 'Player group', value: formatAdminCommunityStatus(game.game_player_group) },
          { label: 'Skill', value: formatAdminCommunityStatus(game.skill_level) },
          { label: 'Environment', value: formatAdminCommunityStatus(game.environment_type) },
          { label: 'Local date', value: game.starts_on_local },
          { label: 'Total spots', value: game.total_spots },
          { label: 'Minimum age', value: game.minimum_age ?? 'None' },
          { label: 'Guests allowed', value: formatAdminCommunityBoolean(game.allow_guests) },
          { label: 'Guests per booking', value: game.max_guests_per_booking },
          { label: 'Host guest maximum', value: game.host_guest_max },
          { label: 'Waitlist', value: formatAdminCommunityBoolean(game.waitlist_enabled) },
          { label: 'Game chat', value: formatAdminCommunityBoolean(game.is_chat_enabled) },
          { label: 'Policy', value: formatAdminCommunityStatus(game.policy_mode) },
          {
            label: 'Published',
            value: formatAdminCommunityDateTime(game.published_at, game.timezone),
          },
          {
            label: 'Cancelled',
            value: formatAdminCommunityDateTime(game.cancelled_at, game.timezone),
          },
          {
            label: 'Completed',
            value: formatAdminCommunityDateTime(game.completed_at, game.timezone),
          },
          {
            label: 'Created',
            value: formatAdminCommunityDateTime(game.created_at, game.timezone),
          },
          {
            label: 'Updated',
            value: formatAdminCommunityDateTime(game.updated_at, game.timezone),
          },
        ]}
      />
    </AdminCommunitySection>
  )
}

function HostContent({ game }) {
  const content = [
    ['Description', game.description],
    ['Custom rules', game.custom_rules_text],
    ['Cancellation policy', game.custom_cancellation_text],
    ['Game notes', game.game_notes],
    ['Parking notes', game.parking_notes],
    ['Cancellation reason', game.cancel_reason],
  ]

  return (
    <AdminCommunitySection icon={FileText} title="Host Content">
      <div className="admin-community-content-list">
        {content.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <p>{value || 'None provided'}</p>
          </div>
        ))}
      </div>
    </AdminCommunitySection>
  )
}

function PaymentSnapshot({ snapshot }) {
  const isHidden = snapshot?.payment_text_moderation_status === 'hidden'

  return (
    <AdminCommunitySection icon={WalletCards} title="Host Payment Snapshot">
      {!snapshot ? (
        <AdminCommunityEmpty>No host payment snapshot found.</AdminCommunityEmpty>
      ) : (
        <div className="admin-community-stack">
          {isHidden && (
            <div className="admin-community-moderation-banner">
              <strong>Hidden from players</strong>
              <span>
                {snapshot.payment_text_hidden_reason || 'No reason recorded'}
              </span>
            </div>
          )}
          <div className="admin-community-methods">
            {snapshot.payment_methods_snapshot.length ? (
              snapshot.payment_methods_snapshot.map((method, index) => (
                <div key={`${method.type || 'method'}-${index}`}>
                  <strong>{formatAdminCommunityStatus(method.type)}</strong>
                  <span>{method.value || 'No value'}</span>
                </div>
              ))
            ) : (
              <AdminCommunityEmpty>No payment methods listed.</AdminCommunityEmpty>
            )}
          </div>
          <div className="admin-community-note-box">
            {snapshot.payment_instructions_snapshot || 'No payment instructions.'}
          </div>
        </div>
      )}
    </AdminCommunitySection>
  )
}

function PublishFee({ publishFee }) {
  return (
    <AdminCommunitySection icon={CreditCard} title="Publish Fee">
      {!publishFee ? (
        <AdminCommunityEmpty>No publish fee record found.</AdminCommunityEmpty>
      ) : (
        <FieldGrid
          fields={[
            { label: 'Fee ID', value: publishFee.id, code: true },
            {
              label: 'Amount',
              value: formatAdminCommunityMoney(publishFee.amount_cents, publishFee.currency),
            },
            { label: 'Status', value: formatAdminCommunityStatus(publishFee.fee_status) },
            { label: 'Waiver', value: formatAdminCommunityStatus(publishFee.waiver_reason) },
            { label: 'Payment status', value: formatAdminCommunityStatus(publishFee.payment_status) },
            { label: 'Paid', value: formatAdminCommunityDateTime(publishFee.paid_at) },
          ]}
        />
      )}
    </AdminCommunitySection>
  )
}

function SupportFlags({
  canResolve,
  flags,
  limit,
  offset,
  onOffsetChange,
  onResolve,
  totalCount,
}) {
  return (
    <AdminCommunitySection count={totalCount} icon={Flag} title="Support Flags">
      {!flags.length ? (
        <AdminCommunityEmpty>No visible support flags.</AdminCommunityEmpty>
      ) : (
        <div className="admin-community-row-stack">
          {flags.map((flag) => (
            <div
              className="admin-community-activity-row admin-community-activity-row--flag"
              key={flag.id}
            >
              <div>
                <strong>{flag.title}</strong>
                <span>{flag.summary}</span>
                {flag.resolution_reason && (
                  <span>Resolution: {flag.resolution_reason}</span>
                )}
              </div>
              <div>
                <span>{formatAdminCommunityStatus(flag.flag_status)}</span>
                <span>
                  {formatAdminCommunityStatus(
                    flag.resolution_outcome || flag.severity,
                  )}
                </span>
              </div>
              <div>
                <span>{formatAdminCommunityDateTime(flag.created_at)}</span>
                <code>{shortAdminCommunityId(flag.id)}</code>
              </div>
              <div className="admin-community-activity-row__action">
                {canResolve &&
                  flag.flag_type === 'community_game_review_required' &&
                  flag.flag_status === 'open' && (
                    <button
                      className="admin-community-button"
                      type="button"
                      onClick={() => onResolve(flag)}
                    >
                      <ClipboardList />
                      Resolve
                    </button>
                  )}
              </div>
            </div>
          ))}
        </div>
      )}
      <CollectionPagination
        label="support flags"
        limit={limit}
        offset={offset}
        onOffsetChange={onOffsetChange}
        pageLength={flags.length}
        totalCount={totalCount}
      />
    </AdminCommunitySection>
  )
}

function AuditActions({
  actions,
  limit,
  offset,
  onOffsetChange,
  totalCount,
}) {
  return (
    <AdminCommunitySection count={totalCount} icon={FileClock} title="Audit History">
      {!actions.length ? (
        <AdminCommunityEmpty>No visible audit actions.</AdminCommunityEmpty>
      ) : (
        <div className="admin-community-row-stack">
          {actions.map((action) => (
            <div className="admin-community-activity-row" key={action.id}>
              <div>
                <strong>{formatAdminCommunityStatus(action.action_type)}</strong>
                <span>{action.reason || 'No reason recorded'}</span>
              </div>
              <div>
                <span>Staff actor</span>
                <code>{shortAdminCommunityId(action.admin_user_id)}</code>
              </div>
              <div>
                <span>{formatAdminCommunityDateTime(action.created_at)}</span>
                <code>{shortAdminCommunityId(action.id)}</code>
              </div>
            </div>
          ))}
        </div>
      )}
      <CollectionPagination
        label="audit actions"
        limit={limit}
        offset={offset}
        onOffsetChange={onOffsetChange}
        pageLength={actions.length}
        totalCount={totalCount}
      />
    </AdminCommunitySection>
  )
}

function ModerationState({ detail, onFlagForReview, onHidePaymentText }) {
  const { capabilities, moderation_state: moderationState } = detail
  const canHidePaymentText = Boolean(
    capabilities.can_hide_unsafe_payment_text &&
    moderationState.host_payment_snapshot_present &&
    !moderationState.unsafe_payment_text_hidden,
  )
  const canFlagForReview = Boolean(
    capabilities.can_flag_game &&
    moderationState.review_flag_status !== 'open',
  )
  const paymentTextState = !moderationState.host_payment_snapshot_present
    ? 'Not present'
    : moderationState.unsafe_payment_text_hidden
      ? 'Hidden'
      : 'Visible'

  return (
    <AdminCommunitySection icon={ClipboardList} title="Moderation State">
      <div className="admin-community-kpis">
        <div>
          <span>Payment text</span>
          <strong>{moderationState.host_payment_snapshot_present ? 'Present' : 'None'}</strong>
        </div>
        <div>
          <span>Unsafe text</span>
          <strong>{paymentTextState}</strong>
        </div>
        <div>
          <span>Review</span>
          <strong>{formatAdminCommunityStatus(moderationState.review_flag_status)}</strong>
        </div>
        <div>
          <span>Cancel</span>
          <strong>{capabilities.can_cancel_game ? 'Allowed' : 'Blocked'}</strong>
        </div>
      </div>
      {moderationState.unsafe_payment_text_hidden && (
        <div className="admin-community-moderation-meta">
          <div>
            <span>Hidden</span>
            <strong>{formatAdminCommunityDateTime(moderationState.payment_text_hidden_at)}</strong>
          </div>
          <div>
            <span>Reason</span>
            <strong>{moderationState.payment_text_hidden_reason || 'No reason recorded'}</strong>
          </div>
        </div>
      )}
      {(canHidePaymentText || canFlagForReview) && (
        <div className="admin-community-action-strip">
          {canFlagForReview && (
            <button
              className="admin-community-button admin-community-button--primary"
              type="button"
              onClick={onFlagForReview}
            >
              <ClipboardList />
              Flag for review
            </button>
          )}
          {canHidePaymentText && (
            <button
              className="admin-community-button admin-community-button--danger"
              type="button"
              onClick={onHidePaymentText}
            >
              <EyeOff />
              Hide payment text
            </button>
          )}
        </div>
      )}
    </AdminCommunitySection>
  )
}

function AdminCommunityGamePage() {
  const { gameId } = useParams()
  const { currentUser } = useAuth()
  const [detail, setDetail] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)
  const [isHidePaymentModalOpen, setIsHidePaymentModalOpen] = useState(false)
  const [reviewModalFlag, setReviewModalFlag] = useState(undefined)
  const [supportFlagOffset, setSupportFlagOffset] = useState(0)
  const [auditOffset, setAuditOffset] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadDetail() {
      if (!currentUser || !gameId) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const nextDetail = await getAdminCommunityGame({
          auditLimit: DETAIL_PAGE_SIZE,
          auditOffset,
          firebaseUser: currentUser,
          gameId,
          supportFlagLimit: DETAIL_PAGE_SIZE,
          supportFlagOffset,
        })

        if (!isMounted) {
          return
        }

        const supportFlagTotalCount = (
          nextDetail.support_flag_total_count ??
          nextDetail.support_flags?.length ??
          0
        )
        if (
          !nextDetail.support_flags?.length &&
          supportFlagOffset > 0 &&
          supportFlagTotalCount > 0
        ) {
          setSupportFlagOffset(Math.max(0, supportFlagOffset - DETAIL_PAGE_SIZE))
          return
        }
        const auditTotalCount = (
          nextDetail.audit_total_count ??
          nextDetail.audit_actions?.length ??
          0
        )
        if (
          !nextDetail.audit_actions?.length &&
          auditOffset > 0 &&
          auditTotalCount > 0
        ) {
          setAuditOffset(Math.max(0, auditOffset - DETAIL_PAGE_SIZE))
          return
        }
        setDetail(nextDetail)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setDetail(null)
        setPageError(error.message || 'Community game could not be loaded.')
        setLoadState('error')
      }
    }

    loadDetail()

    return () => {
      isMounted = false
    }
  }, [auditOffset, currentUser, gameId, refreshCount, supportFlagOffset])

  const title = detail?.game?.title || 'Community Game'

  function handlePaymentTextHidden(result) {
    setDetail((currentDetail) => {
      if (!currentDetail) {
        return currentDetail
      }

      return {
        ...currentDetail,
        payment_snapshot: result.payment_snapshot,
        moderation_state: result.moderation_state,
      }
    })
    setRefreshCount((count) => count + 1)
  }

  return (
    <>
      <AdminWorkspaceLayout
        actions={(
          <div className="admin-community-header-actions">
            <Link className="admin-community-button" to="/admin/community-games">
              <ArrowLeft />
              Back
            </Link>
            <button
              aria-label="Refresh community game"
              className="admin-community-button admin-community-button--icon"
              type="button"
              onClick={() => setRefreshCount((count) => count + 1)}
            >
              <RefreshCw />
            </button>
          </div>
        )}
        breadcrumbs={['Admin', 'Games', 'Community Games']}
        description="Review game, host, participant, payment, and moderation context."
        icon={ShieldAlert}
        title={title}
      >
        <div className="admin-community-detail-layout">
          {pageError && (
            <FormErrorMessage className="admin-community-page-error">
              {pageError}
            </FormErrorMessage>
          )}
          {loadState === 'loading' ? (
            <AdminCommunityGameLoading />
          ) : detail ? (
            <>
              <div className="admin-community-detail-grid">
                <GameSummary detail={detail} />
                <RosterSummary summary={detail.participant_summary} />
              </div>
              <div className="admin-community-detail-grid">
                <GameConfiguration game={detail.game} />
                <HostContent game={detail.game} />
              </div>
              <div
                className={
                  detail.capabilities.can_read_publish_fee
                    ? 'admin-community-detail-grid'
                    : 'admin-community-detail-grid admin-community-detail-grid--single'
                }
              >
                <PaymentSnapshot snapshot={detail.payment_snapshot} />
                {detail.capabilities.can_read_publish_fee && (
                  <PublishFee publishFee={detail.publish_fee} />
                )}
              </div>
              <div className="admin-community-detail-grid">
                <ModerationState
                  detail={detail}
                  onFlagForReview={() => setReviewModalFlag(null)}
                  onHidePaymentText={() => setIsHidePaymentModalOpen(true)}
                />
                <SupportFlags
                  canResolve={detail.capabilities.can_resolve_review_flags}
                  flags={detail.support_flags ?? []}
                  limit={detail.support_flag_limit ?? DETAIL_PAGE_SIZE}
                  offset={detail.support_flag_offset ?? supportFlagOffset}
                  onOffsetChange={setSupportFlagOffset}
                  onResolve={(flag) => setReviewModalFlag(flag)}
                  totalCount={
                    detail.support_flag_total_count ??
                    detail.support_flags?.length ??
                    0
                  }
                />
              </div>
              <AuditActions
                actions={detail.audit_actions ?? []}
                limit={detail.audit_limit ?? DETAIL_PAGE_SIZE}
                offset={detail.audit_offset ?? auditOffset}
                onOffsetChange={setAuditOffset}
                totalCount={detail.audit_total_count ?? detail.audit_actions?.length ?? 0}
              />
            </>
          ) : null}
        </div>
      </AdminWorkspaceLayout>
      {detail && isHidePaymentModalOpen && (
        <AdminCommunityGameHidePaymentTextModal
          detail={detail}
          firebaseUser={currentUser}
          onClose={() => setIsHidePaymentModalOpen(false)}
          onHidden={handlePaymentTextHidden}
        />
      )}
      {detail && reviewModalFlag !== undefined && (
        <AdminCommunityGameReviewModal
          detail={detail}
          firebaseUser={currentUser}
          flag={reviewModalFlag}
          onClose={() => setReviewModalFlag(undefined)}
          onCompleted={() => setRefreshCount((count) => count + 1)}
        />
      )}
    </>
  )
}

export default AdminCommunityGamePage
