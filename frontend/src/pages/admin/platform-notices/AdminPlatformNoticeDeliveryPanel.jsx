import { useEffect, useState } from 'react'
import {
  BellRing,
  ChevronLeft,
  ChevronRight,
  Clock3,
  RefreshCw,
  RotateCcw,
  Send,
  UsersRound,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import '../../../styles/admin/AdminPlatformNoticeDelivery.css'
import {
  listPlatformNoticeCampaignAttempts,
  listPlatformNoticeCampaignDeliveries,
} from '../shared/adminApi.js'
import AdminPlatformNoticeDeliveryModal from './AdminPlatformNoticeDeliveryModal.jsx'
import {
  PLATFORM_NOTICE_DELIVERY_STATUS_OPTIONS,
  formatPlatformNoticeDateTime,
  formatPlatformNoticeLabel,
  shortPlatformNoticeId,
} from './adminPlatformNoticeData.js'

const DELIVERY_PAGE_LIMIT = 20

function DeliveryStatus({ status }) {
  return (
    <span className={`admin-platform-notices-delivery-status admin-platform-notices-delivery-status--${status}`}>
      {formatPlatformNoticeLabel(status)}
    </span>
  )
}

function DeliveryPagination({
  itemCount,
  offset,
  onOffsetChange,
  totalCount,
}) {
  if (!totalCount) {
    return null
  }

  return (
    <nav className="admin-platform-notices-delivery-pagination">
      <span>
        {offset + 1}-{Math.min(offset + itemCount, totalCount)} of {totalCount}
      </span>
      <div>
        <button
          aria-label="Previous delivery page"
          disabled={offset === 0}
          title="Previous page"
          type="button"
          onClick={() => onOffsetChange(Math.max(0, offset - DELIVERY_PAGE_LIMIT))}
        >
          <ChevronLeft />
        </button>
        <button
          aria-label="Next delivery page"
          disabled={offset + itemCount >= totalCount}
          title="Next page"
          type="button"
          onClick={() => onOffsetChange(offset + DELIVERY_PAGE_LIMIT)}
        >
          <ChevronRight />
        </button>
      </div>
    </nav>
  )
}

function DeliveryRows({ deliveries }) {
  return (
    <div className="admin-platform-notices-delivery-rows">
      {deliveries.map((delivery) => (
        <div className="admin-platform-notices-delivery-row" key={delivery.id}>
          <span className="admin-platform-notices-delivery-row__icon">
            <UsersRound />
          </span>
          <span className="admin-platform-notices-delivery-row__copy">
            <strong>Recipient {shortPlatformNoticeId(delivery.recipient_user_id_snapshot)}</strong>
            <small>{delivery.recipient_user_id_snapshot}</small>
          </span>
          <span className="admin-platform-notices-delivery-row__meta">
            <DeliveryStatus status={delivery.delivery_status} />
            <small>
              {delivery.skip_reason
                ? formatPlatformNoticeLabel(delivery.skip_reason)
                : delivery.failure_code
                  ? formatPlatformNoticeLabel(delivery.failure_code)
                  : `${delivery.attempt_count} ${delivery.attempt_count === 1 ? 'attempt' : 'attempts'}`}
            </small>
          </span>
        </div>
      ))}
    </div>
  )
}

function AttemptRows({ attempts }) {
  return (
    <div className="admin-platform-notices-delivery-rows">
      {attempts.map((attempt) => (
        <div className="admin-platform-notices-delivery-row" key={attempt.id}>
          <span className="admin-platform-notices-delivery-row__icon">
            <Clock3 />
          </span>
          <span className="admin-platform-notices-delivery-row__copy">
            <strong>{formatPlatformNoticeLabel(attempt.attempt_type)}</strong>
            <small>{formatPlatformNoticeDateTime(attempt.started_at)}</small>
          </span>
          <span className="admin-platform-notices-delivery-row__meta">
            <DeliveryStatus status={attempt.attempt_status} />
            <small>
              {attempt.delivered_count} delivered · {attempt.skipped_count} skipped · {attempt.failed_count} failed
            </small>
          </span>
        </div>
      ))}
    </div>
  )
}

function AdminPlatformNoticeDeliveryPanel({
  campaign,
  currentUser,
  onCampaignUpdated,
}) {
  const [activeView, setActiveView] = useState('deliveries')
  const [attemptOffset, setAttemptOffset] = useState(0)
  const [attempts, setAttempts] = useState([])
  const [attemptTotal, setAttemptTotal] = useState(0)
  const [deliveryFilter, setDeliveryFilter] = useState('')
  const [deliveryOffset, setDeliveryOffset] = useState(0)
  const [deliveries, setDeliveries] = useState([])
  const [deliveryTotal, setDeliveryTotal] = useState(0)
  const [error, setError] = useState('')
  const [loadState, setLoadState] = useState('idle')
  const [modalOperation, setModalOperation] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)
  const [successMessage, setSuccessMessage] = useState('')
  const summary = campaign.delivery_summary || {}
  const hasDeliveryHistory = campaign.campaign_status !== 'draft'
  const canRetry = ['completed_with_failures', 'failed'].includes(
    campaign.campaign_status,
  ) && (summary.failed_count || 0) > 0

  useEffect(() => {
    let isMounted = true

    async function loadDeliveryHistory() {
      if (!currentUser || !hasDeliveryHistory) {
        setAttempts([])
        setDeliveries([])
        setAttemptTotal(0)
        setDeliveryTotal(0)
        setError('')
        setLoadState('idle')
        return
      }

      setLoadState('loading')
      setError('')
      try {
        const response = activeView === 'deliveries'
          ? await listPlatformNoticeCampaignDeliveries({
            campaignId: campaign.id,
            deliveryStatus: deliveryFilter,
            firebaseUser: currentUser,
            limit: DELIVERY_PAGE_LIMIT,
            offset: deliveryOffset,
          })
          : await listPlatformNoticeCampaignAttempts({
            campaignId: campaign.id,
            firebaseUser: currentUser,
            limit: DELIVERY_PAGE_LIMIT,
            offset: attemptOffset,
          })
        if (!isMounted) {
          return
        }

        if (activeView === 'deliveries') {
          setDeliveries(response.deliveries || [])
          setDeliveryTotal(response.total_count || 0)
        } else {
          setAttempts(response.attempts || [])
          setAttemptTotal(response.total_count || 0)
        }
        setLoadState('ready')
      } catch (requestError) {
        if (isMounted) {
          setError(requestError.message || 'Delivery history could not be loaded.')
          setLoadState('error')
        }
      }
    }

    loadDeliveryHistory()
    return () => {
      isMounted = false
    }
  }, [
    activeView,
    attemptOffset,
    campaign.id,
    currentUser,
    deliveryFilter,
    deliveryOffset,
    hasDeliveryHistory,
    refreshCount,
  ])

  function handleDeliveryComplete(result) {
    setDeliveryFilter('')
    setDeliveryOffset(0)
    setAttemptOffset(0)
    setSuccessMessage(
      result.attempt?.attempt_type === 'retry_failed'
        ? 'Failed deliveries retried.'
        : 'Campaign sent.',
    )
    onCampaignUpdated(result.campaign)
    setRefreshCount((count) => count + 1)
  }

  function selectView(view) {
    setActiveView(view)
    setError('')
    setSuccessMessage('')
  }

  return (
    <section className="admin-platform-notices-delivery">
      <header className="admin-platform-notices-delivery__heading">
        <div>
          <BellRing />
          <h3>Delivery</h3>
        </div>
        <div>
          {hasDeliveryHistory && (
            <button
              aria-label="Refresh delivery history"
              title="Refresh delivery history"
              type="button"
              onClick={() => setRefreshCount((count) => count + 1)}
            >
              <RefreshCw />
            </button>
          )}
          {campaign.campaign_status === 'draft' && (
            <button
              className="admin-platform-notices-button admin-platform-notices-button--primary"
              type="button"
              onClick={() => setModalOperation('send')}
            >
              <Send />
              Send Campaign
            </button>
          )}
          {canRetry && (
            <button
              className="admin-platform-notices-button"
              type="button"
              onClick={() => setModalOperation('retry')}
            >
              <RotateCcw />
              Retry Failed
            </button>
          )}
        </div>
      </header>

      <div className="admin-platform-notices-delivery-summary">
        {[
          ['Targeted', summary.targeted_count || 0],
          ['Delivered', summary.delivered_count || 0],
          ['Skipped', summary.skipped_count || 0],
          ['Failed', summary.failed_count || 0],
        ].map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>

      {successMessage && (
        <p className="admin-platform-notices-success" role="status">
          {successMessage}
        </p>
      )}

      {!hasDeliveryHistory ? (
        <div className="admin-platform-notices-delivery-empty">
          <BellRing />
          <span>No delivery attempts.</span>
        </div>
      ) : (
        <>
          <div className="admin-platform-notices-delivery-toolbar">
            <div className="admin-platform-notices-delivery-tabs" role="tablist">
              <button
                aria-selected={activeView === 'deliveries'}
                className={activeView === 'deliveries' ? 'is-active' : ''}
                role="tab"
                type="button"
                onClick={() => selectView('deliveries')}
              >
                Recipients
              </button>
              <button
                aria-selected={activeView === 'attempts'}
                className={activeView === 'attempts' ? 'is-active' : ''}
                role="tab"
                type="button"
                onClick={() => selectView('attempts')}
              >
                Attempts
              </button>
            </div>
            {activeView === 'deliveries' && (
              <select
                aria-label="Filter recipients by delivery status"
                value={deliveryFilter}
                onChange={(event) => {
                  setDeliveryFilter(event.target.value)
                  setDeliveryOffset(0)
                }}
              >
                {PLATFORM_NOTICE_DELIVERY_STATUS_OPTIONS.map((option) => (
                  <option key={option.value || 'all'} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            )}
          </div>

          <FormErrorMessage>{error}</FormErrorMessage>
          {loadState === 'loading' && (
            <div className="admin-platform-notices-delivery-loading" role="status">
              {Array.from({ length: 3 }).map((_, index) => (
                <SkeletonBlock height="3.5rem" key={index} rounded width="100%" />
              ))}
            </div>
          )}
          {loadState === 'ready' && activeView === 'deliveries' && (
            deliveries.length
              ? <DeliveryRows deliveries={deliveries} />
              : <div className="admin-platform-notices-delivery-empty"><span>No recipients found.</span></div>
          )}
          {loadState === 'ready' && activeView === 'attempts' && (
            attempts.length
              ? <AttemptRows attempts={attempts} />
              : <div className="admin-platform-notices-delivery-empty"><span>No attempts found.</span></div>
          )}

          {activeView === 'deliveries' ? (
            <DeliveryPagination
              itemCount={deliveries.length}
              offset={deliveryOffset}
              onOffsetChange={setDeliveryOffset}
              totalCount={deliveryTotal}
            />
          ) : (
            <DeliveryPagination
              itemCount={attempts.length}
              offset={attemptOffset}
              onOffsetChange={setAttemptOffset}
              totalCount={attemptTotal}
            />
          )}
        </>
      )}

      {modalOperation && (
        <AdminPlatformNoticeDeliveryModal
          campaign={campaign}
          currentUser={currentUser}
          operation={modalOperation}
          onClose={() => setModalOperation('')}
          onComplete={handleDeliveryComplete}
        />
      )}
    </section>
  )
}

export default AdminPlatformNoticeDeliveryPanel
