import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  EyeOff,
  FileClock,
  Flag,
  MessageSquareText,
  ShieldAlert,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import {
  GameDateIcon,
  GameDurationIcon,
  GameEnvironmentIcon,
  GameSpotsIcon,
  GameFormatIcon,
  GameIndoorIcon,
  GameOutdoorIcon,
  GamePlayerGroupIcon,
  GameSkillIcon,
  GameTimeIcon,
  PriceIcon,
  VenueIcon,
} from '../../../components/GameFactIcons.jsx'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminCommunityGames.css'
import AdminChatModerationPanel from '../shared/AdminChatModerationPanel.jsx'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import {
  getAdminCommunityGame,
  getAdminCommunityGameChatSummary,
  listAdminCommunityGameChatModerationMessages,
  moderateAdminCommunityGameChatMessage,
} from '../shared/adminApi.js'
import {
  ADMIN_PERMISSIONS,
  hasAdminPermission,
} from '../shared/adminWorkspaceData.js'
import { useAdminAccess } from '../shared/useAdminAccess.js'
import {
  formatAdminCommunityDateTime,
  formatAdminCommunityMoney,
  formatAdminCommunityStatus,
} from './adminCommunityGameFormatters.js'
import AdminCommunityGameHidePaymentTextModal from './AdminCommunityGameHidePaymentTextModal.jsx'
import AdminCommunityGameReviewModal from './AdminCommunityGameReviewModal.jsx'

const DETAIL_PAGE_SIZE = 50
const COMMUNITY_DETAIL_TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'review', label: 'Review' },
  { id: 'chat', label: 'Chat' },
  { id: 'audit', label: 'Audit' },
]

function AdminCommunitySection({ children, count, icon: Icon, title }) {
  return (
    <section className="admin-community-section">
      <div className="admin-community-section__heading">
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

function AdminCommunityEmptyState({ children, icon: Icon, title }) {
  return (
    <div className="admin-community-empty-state">
      {Icon && (
        <span className="admin-community-empty-state__icon">
          <Icon />
        </span>
      )}
      <div>
        <strong>{title}</strong>
        {children && <p>{children}</p>}
      </div>
    </div>
  )
}

function AdminCommunityRecordSection({ children, icon: Icon, title }) {
  return (
    <section className="admin-community-record-section">
      <div className="admin-community-record-section__heading">
        <Icon />
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  )
}

function AdminCommunityChatSummary({ firebaseUser, gameId }) {
  const [summary, setSummary] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [loadError, setLoadError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)

  const loadChatMessages = useCallback((options) => (
    listAdminCommunityGameChatModerationMessages({
      ...options,
      gameId,
    })
  ), [gameId])

  const moderateChatMessage = useCallback((options) => (
    moderateAdminCommunityGameChatMessage({
      ...options,
      gameId,
    })
  ), [gameId])

  const refreshChatSummary = useCallback(() => {
    setRefreshCount((count) => count + 1)
  }, [])

  useEffect(() => {
    let isMounted = true

    async function loadSummary() {
      if (!firebaseUser || !gameId) return
      setLoadState('loading')
      setLoadError('')
      try {
        const response = await getAdminCommunityGameChatSummary({
          firebaseUser,
          gameId,
        })
        if (!isMounted) return
        setSummary(response)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) return
        setSummary(null)
        setLoadError(error.message || 'Game chat summary could not be loaded.')
        setLoadState('error')
      }
    }

    loadSummary()
    return () => {
      isMounted = false
    }
  }, [firebaseUser, gameId, refreshCount])

  return (
    <AdminCommunitySection icon={MessageSquareText} title="Game Chat">
      {loadState === 'loading' && <AdminCommunityEmpty>Loading chat summary.</AdminCommunityEmpty>}
      {loadError && <p className="admin-community-alert">{loadError}</p>}
      {loadState === 'ready' && summary && (
        <div className="admin-community-chat-summary">
          <div className="admin-community-chat-summary-grid">
            <div>
              <span>Status</span>
              <strong>{formatAdminCommunityStatus(summary.chat_status)}</strong>
            </div>
            <div>
              <span>Visible</span>
              <strong>{summary.message_count}</strong>
            </div>
            <div>
              <span>Needs review</span>
              <strong>{summary.needs_review_count}</strong>
            </div>
            <div>
              <span>Removed</span>
              <strong>{summary.removed_count}</strong>
            </div>
          </div>
          <AdminChatModerationPanel
            firebaseUser={firebaseUser}
            formatDateTime={formatAdminCommunityDateTime}
            loadMessages={loadChatMessages}
            moderateMessage={moderateChatMessage}
            needsReviewCount={summary.needs_review_count}
            onAfterAction={refreshChatSummary}
            refreshToken={refreshCount}
            removedMessageCount={summary.removed_count}
            visibleMessageCount={summary.message_count}
          />
        </div>
      )}
    </AdminCommunitySection>
  )
}

function AdminCommunityChatLocked({ isLoading }) {
  return (
    <AdminCommunitySection icon={MessageSquareText} title="Game Chat">
      <AdminCommunityEmptyState
        icon={MessageSquareText}
        title={isLoading ? 'Loading chat access' : 'Chat access required'}
      >
        {isLoading
          ? 'Loading chat access.'
          : 'Content moderation permission is required for chat inspection.'}
      </AdminCommunityEmptyState>
    </AdminCommunitySection>
  )
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

function getDisplayValue(value, fallback = 'None') {
  return value === null || value === undefined || value === '' ? fallback : value
}

function hasDisplayValue(value) {
  if (value === null || value === undefined) return false
  if (typeof value === 'string') return value.trim().length > 0
  return value !== ''
}

function formatAdminCommunityOptionalDateTime(value, timeZone = undefined) {
  return value ? formatAdminCommunityDateTime(value, timeZone) : 'None'
}

function formatAdminCommunityGameDate(game) {
  if (!game.starts_at && !game.ends_at) return 'None'

  const value = new Date(game.starts_at ?? game.ends_at)
  if (Number.isNaN(value.getTime())) {
    return 'Invalid date'
  }

  const timeZoneOptions = game.timezone ? { timeZone: game.timezone } : {}
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    ...timeZoneOptions,
  }).format(value)
}

function formatAdminCommunityTimeRange(game) {
  if (!game.starts_at && !game.ends_at) return 'None'

  const start = game.starts_at ? new Date(game.starts_at) : null
  const end = game.ends_at ? new Date(game.ends_at) : null
  if ((start && Number.isNaN(start.getTime())) || (end && Number.isNaN(end.getTime()))) {
    return 'Invalid date'
  }

  const timeZoneOptions = game.timezone ? { timeZone: game.timezone } : {}
  const timeFormatter = new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    ...timeZoneOptions,
  })

  if (start && end) {
    return `${timeFormatter.format(start)} - ${timeFormatter.format(end)}`
  }

  const value = start ?? end
  return timeFormatter.format(value)
}

function formatAdminCommunityDuration(game) {
  if (!game.starts_at || !game.ends_at) return 'None'

  const start = new Date(game.starts_at)
  const end = new Date(game.ends_at)
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return 'Invalid duration'
  }

  const durationMinutes = Math.max(0, Math.round((end.getTime() - start.getTime()) / 60000))
  if (!durationMinutes) return 'None'
  if (durationMinutes < 60) return `${durationMinutes} min`

  const hours = Math.floor(durationMinutes / 60)
  const minutes = durationMinutes % 60
  return minutes ? `${hours} hr ${minutes} min` : `${hours} hr`
}

function formatCommunityPaymentMode(value) {
  const labels = {
    external_host: 'Players pay host',
    free: 'No player payment',
    in_app: 'In-app payment',
    none: 'No player payment',
  }
  return labels[value] || formatAdminCommunityStatus(value)
}

function formatCommunityPaymentSummary(game) {
  const priceInCents = Number(game.price_per_player_cents || 0)
  const paymentMode = formatCommunityPaymentMode(game.payment_collection_type)

  if (priceInCents <= 0) {
    return paymentMode
  }

  return `${formatAdminCommunityMoney(priceInCents, game.currency)} · ${paymentMode}`
}

function formatPaymentInfoState(moderationState) {
  if (moderationState.unsafe_payment_text_hidden) return 'Hidden from players'
  if (moderationState.host_payment_snapshot_present) return 'Visible to players'
  return 'No payment info'
}

function formatReviewStatus(value) {
  const labels = {
    not_flagged: 'Not flagged',
    open: 'Review open',
    resolved: 'Resolved',
  }
  return labels[value] || formatAdminCommunityStatus(value)
}

function formatPublishFeeResult(publishFee, canRead) {
  if (!canRead) return 'Not available'
  if (!publishFee) return 'No publish fee record'
  if (publishFee.waiver_reason === 'first_game_free') return 'Free first community game'
  if (publishFee.waiver_reason === 'admin_comp') return 'Waived by admin'
  if (publishFee.fee_status === 'paid') return 'Paid'
  if (publishFee.fee_status === 'waived') return 'Waived'
  return formatAdminCommunityStatus(publishFee.fee_status)
}

function formatAdminCommunityActionLabel(value) {
  const labels = {
    append_audit_note: 'Audit note',
    cancel_game: 'Cancel game',
    hide_unsafe_community_payment_text: 'Hide payment info',
    resolve_support_flag: 'Resolve review flag',
  }
  return labels[value] || formatAdminCommunityStatus(value)
}

function formatCommunityOverviewStatus(game) {
  const lifecycleStatus = formatAdminCommunityStatus(game.game_status)

  if (game.publish_status === 'published') {
    return lifecycleStatus
  }

  return `${lifecycleStatus} · ${formatAdminCommunityStatus(game.publish_status)}`
}

function formatCommunityHostPaymentMethods(game, snapshot) {
  const paymentMethods = snapshot?.payment_methods_snapshot || []

  if (paymentMethods.length) {
    return paymentMethods
      .map((method) => {
        const typeLabel = formatAdminCommunityStatus(method.type)
        return method.value ? `${typeLabel}: ${method.value}` : typeLabel
      })
      .join(' · ')
  }

  if (Number(game.price_per_player_cents || 0) <= 0) {
    return 'None required'
  }

  return 'No payment methods provided'
}

function formatCommunityPublishFeeSummary(publishFee, canRead) {
  if (!canRead) return null
  if (!publishFee) return 'No publish fee record'

  const statusLabel = formatPublishFeeResult(publishFee, canRead)
  const amountLabel = formatAdminCommunityMoney(publishFee.amount_cents, publishFee.currency)
  return `${statusLabel} · ${amountLabel}`
}

function OverviewTextRow({ label, value }) {
  return (
    <div>
      <span>{label}</span>
      <p>{hasDisplayValue(value) ? value : 'None provided'}</p>
    </div>
  )
}

function SummaryItem({ children, icon: Icon, label }) {
  return (
    <div className="admin-community-summary__item">
      <Icon />
      <span className="admin-community-summary__copy">
        <small>{label}</small>
        <span className="admin-community-summary__value">{children}</span>
      </span>
    </div>
  )
}

function CommunityGameSummary({ detail }) {
  const { game, participant_summary: participantSummary } = detail
  const EnvironmentIcon =
    game.environment_type === 'outdoor'
      ? GameOutdoorIcon
      : game.environment_type === 'indoor'
        ? GameIndoorIcon
        : GameEnvironmentIcon

  return (
    <section className="admin-community-summary" aria-label="Community game summary">
      <div className="admin-community-summary__header">
        <div className="admin-community-summary__identity">
          <span>Community Game</span>
          <h2>{game.title || 'Community Game'}</h2>
        </div>
      </div>

      <div className="admin-community-summary__grid">
        <SummaryItem icon={GameDateIcon} label="Date">
          {formatAdminCommunityGameDate(game)}
        </SummaryItem>
        <SummaryItem icon={GameTimeIcon} label="Time">
          {formatAdminCommunityTimeRange(game)}
        </SummaryItem>
        <SummaryItem icon={GameDurationIcon} label="Duration">
          {formatAdminCommunityDuration(game)}
        </SummaryItem>
        <SummaryItem icon={EnvironmentIcon} label="Environment">
          {formatAdminCommunityStatus(game.environment_type)}
        </SummaryItem>
        <SummaryItem icon={GameFormatIcon} label="Format">
          {game.format_label || 'Pickup'}
        </SummaryItem>
        <SummaryItem icon={GamePlayerGroupIcon} label="Player group">
          {formatAdminCommunityStatus(game.game_player_group)}
        </SummaryItem>
        <SummaryItem icon={GameSkillIcon} label="Skill">
          {formatAdminCommunityStatus(game.skill_level)}
        </SummaryItem>
        <SummaryItem icon={PriceIcon} label="Price">
          {formatCommunityPaymentSummary(game)}
        </SummaryItem>
        <SummaryItem icon={GameSpotsIcon} label="Roster">
          {participantSummary.confirmed_count}/{game.total_spots}
        </SummaryItem>
        <SummaryItem icon={VenueIcon} label="Venue">
          {game.venue_name_snapshot || 'Venue unavailable'}
        </SummaryItem>
      </div>
    </section>
  )
}

function FieldList({ className = '', fields, layout }) {
  const listClassName = [
    'admin-community-field-list',
    layout ? `admin-community-field-list--${layout}` : '',
    className,
  ].filter(Boolean).join(' ')

  return (
    <div className={listClassName}>
      {fields.map((field) => (
        <div className="admin-community-field" key={field.label}>
          <span>{field.label}</span>
          <strong>{getDisplayValue(field.value)}</strong>
        </div>
      ))}
    </div>
  )
}

function CommunityOverview({ detail }) {
  const {
    capabilities,
    game,
    host,
    participant_summary: participantSummary,
    payment_snapshot: paymentSnapshot,
    publish_fee: publishFee,
  } = detail
  const publishFeeSummary = formatCommunityPublishFeeSummary(
    publishFee,
    capabilities.can_read_publish_fee,
  )
  const overviewFields = [
    { label: 'Status', value: formatCommunityOverviewStatus(game) },
    { label: 'Host', value: host?.display_name || 'No host' },
    { label: 'Host eligibility', value: formatAdminCommunityStatus(host?.hosting_status) },
    { label: 'Address', value: game.address_snapshot },
    { label: 'Neighborhood', value: game.neighborhood_snapshot || 'None' },
    { label: 'Registered players', value: participantSummary.registered_user_count },
    { label: 'Guests', value: participantSummary.guest_count },
    { label: 'Waitlisted players', value: participantSummary.waitlisted_count },
    {
      label: 'Host payment methods',
      value: formatCommunityHostPaymentMethods(game, paymentSnapshot),
    },
  ]

  if (publishFeeSummary) {
    overviewFields.push({ label: 'Host publish fee', value: publishFeeSummary })
  }

  return (
    <section className="admin-community-record-panel">
      <AdminCommunityRecordSection icon={ClipboardList} title="Overview">
        <FieldList fields={overviewFields} layout="three" />
        <div className="admin-community-content-list">
          <OverviewTextRow label="Game notes" value={game.game_notes} />
          <OverviewTextRow label="Host rules" value={game.custom_rules_text} />
          <OverviewTextRow label="Parking notes" value={game.parking_notes} />
          {hasDisplayValue(game.cancel_reason) && (
            <OverviewTextRow label="Cancellation reason" value={game.cancel_reason} />
          )}
        </div>
      </AdminCommunityRecordSection>
    </section>
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
    <AdminCommunitySection count={totalCount} icon={Flag} title="Review Flags">
      {!flags.length ? (
        <AdminCommunityEmptyState icon={Flag} title="No review flags">
          Review flags will appear here when staff or automation marks this game for attention.
        </AdminCommunityEmptyState>
      ) : (
        <div className="admin-community-row-stack">
          {flags.map((flag) => (
            <div
              className="admin-community-activity-row admin-community-activity-row--flag"
              key={flag.id}
            >
              <div className="admin-community-activity-row__main">
                <span>Review item</span>
                <strong>{flag.title || 'Review flag'}</strong>
                <p>{flag.summary || 'No summary recorded'}</p>
              </div>
              <div className="admin-community-activity-facts">
                <div>
                  <span>Status</span>
                  <strong>{formatAdminCommunityStatus(flag.flag_status)}</strong>
                </div>
                <div>
                  <span>Created</span>
                  <strong>{formatAdminCommunityDateTime(flag.created_at)}</strong>
                </div>
                <div>
                  <span>Resolution outcome</span>
                  <strong>{flag.resolution_outcome ? formatAdminCommunityStatus(flag.resolution_outcome) : 'None'}</strong>
                </div>
                <div>
                  <span>Resolution reason</span>
                  <strong>{flag.resolution_reason || 'None'}</strong>
                </div>
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
        label="review flags"
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
        <AdminCommunityEmptyState icon={FileClock} title="No audit actions">
          Staff-visible audit entries will appear here once recorded.
        </AdminCommunityEmptyState>
      ) : (
        <div className="admin-community-row-stack">
          {actions.map((action) => (
            <div className="admin-community-activity-row admin-community-activity-row--audit" key={action.id}>
              <div className="admin-community-activity-row__main">
                <span>Action</span>
                <strong>{formatAdminCommunityActionLabel(action.action_type)}</strong>
                <p>{action.reason || 'No reason recorded'}</p>
              </div>
              <div className="admin-community-activity-facts">
                <div>
                  <span>Staff</span>
                  <strong>Staff user</strong>
                </div>
                <div>
                  <span>Date</span>
                  <strong>{formatAdminCommunityDateTime(action.created_at)}</strong>
                </div>
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

  return (
    <AdminCommunitySection icon={ClipboardList} title="Safety Review">
      <FieldList
        className="admin-community-review-facts"
        layout="four"
        fields={[
          { label: 'Review status', value: formatReviewStatus(moderationState.review_flag_status) },
          { label: 'Payment info', value: formatPaymentInfoState(moderationState) },
          {
            label: 'Hidden date',
            value: formatAdminCommunityOptionalDateTime(
              moderationState.payment_text_hidden_at,
            ),
          },
          {
            label: 'Hidden reason',
            value: moderationState.payment_text_hidden_reason || 'None',
          },
        ]}
      />
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
              Hide payment info
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
  const { adminAccess, isLoading: isAdminAccessLoading } = useAdminAccess()
  const [detail, setDetail] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)
  const [isHidePaymentModalOpen, setIsHidePaymentModalOpen] = useState(false)
  const [reviewModalFlag, setReviewModalFlag] = useState(undefined)
  const [supportFlagOffset, setSupportFlagOffset] = useState(0)
  const [auditOffset, setAuditOffset] = useState(0)
  const [activeTab, setActiveTab] = useState('overview')

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

  const title = 'Manage Community Game'
  const canViewChat = hasAdminPermission(
    adminAccess,
    ADMIN_PERMISSIONS.CONTENT_MODERATE,
  )

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
          </div>
        )}
        breadcrumbs={['Admin', 'Games', 'Community Games']}
        description="Review community game status, roster, payment info, safety review, and audit history."
        headerClassName="admin-community-page-header"
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
              <CommunityGameSummary detail={detail} />
              <nav
                className="admin-community-detail-tabs"
                aria-label="Community game management"
              >
                {COMMUNITY_DETAIL_TABS.map((tab) => (
                  <button
                    key={tab.id}
                    aria-selected={activeTab === tab.id}
                    className={activeTab === tab.id ? 'is-active' : ''}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                  >
                    {tab.label}
                  </button>
                ))}
              </nav>

              {activeTab === 'overview' && (
                <div className="admin-community-tab-panel">
                  <CommunityOverview detail={detail} />
                </div>
              )}

              {activeTab === 'review' && (
                <div className="admin-community-main-stack admin-community-tab-panel">
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
              )}

              {activeTab === 'chat' && (
                <div className="admin-community-tab-panel">
                  {canViewChat ? (
                    <AdminCommunityChatSummary
                      firebaseUser={currentUser}
                      gameId={detail.game.id}
                    />
                  ) : (
                    <AdminCommunityChatLocked isLoading={isAdminAccessLoading} />
                  )}
                </div>
              )}

              {activeTab === 'audit' && (
                <div className="admin-community-tab-panel">
                  <AuditActions
                    actions={detail.audit_actions ?? []}
                    limit={detail.audit_limit ?? DETAIL_PAGE_SIZE}
                    offset={detail.audit_offset ?? auditOffset}
                    onOffsetChange={setAuditOffset}
                    totalCount={detail.audit_total_count ?? detail.audit_actions?.length ?? 0}
                  />
                </div>
              )}
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
