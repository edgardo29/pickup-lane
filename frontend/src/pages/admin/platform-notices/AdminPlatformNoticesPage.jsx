import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  Bell,
  ChevronLeft,
  ChevronRight,
  Megaphone,
  RefreshCw,
  Search,
  Send,
  UserPlus,
  X,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminPlatformNotices.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import {
  cancelPlatformNotice,
  createPlatformNotice,
  getPlatformNotice,
  listAdminLookupUsers,
  listPlatformNoticeRecipients,
  listPlatformNotices,
} from '../shared/adminApi.js'
import {
  AUDIENCE_TYPE_ALL_ELIGIBLE,
  AUDIENCE_TYPE_SELECTED,
  EMPTY_PLATFORM_NOTICE_FILTERS,
  EMPTY_PLATFORM_NOTICE_FORM,
  PLATFORM_NOTICE_HISTORY_SEARCH_MAX_LENGTH,
  PLATFORM_NOTICE_HISTORY_SEARCH_MIN_MEANINGFUL_CHARS,
  PLATFORM_NOTICE_SELECTED_USER_LIMIT,
  PLATFORM_NOTICE_STATUS_OPTIONS,
  buildPlatformNoticeCancelPayload,
  buildPlatformNoticeCreatePayload,
  canAddPlatformNoticeSelectedUser,
  createPlatformNoticeIdempotencyKey,
  formatPlatformNoticeDateTime,
  getActivePlatformNoticeHistorySearch,
  platformNoticeAudienceLabel,
  platformNoticeStatusLabel,
  userDisplayName,
  validatePlatformNoticeAudience,
  validatePlatformNoticeContent,
} from './adminPlatformNoticeData.js'

const HISTORY_LIMIT = 30
const HISTORY_SEARCH_DEBOUNCE_MS = 300
const RECIPIENT_LIMIT = 50
const USER_LOOKUP_LIMIT = 10
const USER_SEARCH_DEBOUNCE_MS = 300
const USER_SEARCH_MIN_LENGTH = 3

const NOTICE_STEPS = [
  { key: 'write', label: 'Write Notice' },
  { key: 'audience', label: 'Choose Audience' },
  { key: 'review', label: 'Review & Publish' },
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

function NoticeStepRail({ activeStep }) {
  const activeIndex = NOTICE_STEPS.findIndex((step) => step.key === activeStep)

  return (
    <ol className="platform-notices-steps" aria-label="Platform notice steps">
      {NOTICE_STEPS.map((step, index) => {
        const className = [
          'platform-notices-step',
          step.key === activeStep ? 'active' : '',
          index < activeIndex ? 'complete' : '',
        ].filter(Boolean).join(' ')

        return (
          <li className={className} key={step.key}>
            <span className="platform-notices-step__content">
              <span className="platform-notices-step__marker">{index + 1}</span>
              <strong>{step.label}</strong>
            </span>
          </li>
        )
      })}
    </ol>
  )
}

function NoticePreview({ message, title }) {
  const previewTitle = title.trim() || 'Notice title'
  const previewMessage = message.trim() || 'Notice message preview.'

  return (
    <aside className="platform-notices-preview" aria-label="Notice preview">
      <div className="platform-notices-preview__heading">
        <span className="platform-notices-preview__icon" aria-hidden="true">
          <Bell />
        </span>
        <div>
          <span>[PICKUP LANE]</span>
          <h3>{previewTitle}</h3>
        </div>
      </div>
      <div className="platform-notices-preview__message">
        <span>Message</span>
        <p>{previewMessage}</p>
      </div>
    </aside>
  )
}

function PageTabs({ activeMode, onChange }) {
  return (
    <div className="app-tabs platform-notices-tabs" role="tablist">
      <button
        className={activeMode === 'create' ? 'active' : ''}
        type="button"
        onClick={() => onChange('create')}
      >
        Create Notice
      </button>
      <button
        className={activeMode === 'history' ? 'active' : ''}
        type="button"
        onClick={() => onChange('history')}
      >
        History
      </button>
    </div>
  )
}

function PrimaryButton({ children, disabled = false, icon: Icon, onClick, type = 'button' }) {
  return (
    <button
      className="platform-notices-button platform-notices-button--primary"
      disabled={disabled}
      type={type}
      onClick={onClick}
    >
      {Icon && <Icon aria-hidden="true" />}
      {children}
    </button>
  )
}

function SecondaryButton({ children, disabled = false, icon: Icon, onClick, type = 'button' }) {
  return (
    <button
      className="platform-notices-button"
      disabled={disabled}
      type={type}
      onClick={onClick}
    >
      {Icon && <Icon aria-hidden="true" />}
      {children}
    </button>
  )
}

function FieldShell({ children, label }) {
  return (
    <label className="platform-notices-field">
      <span>{label}</span>
      {children}
    </label>
  )
}

function WriteNoticeStep({ error, form, onContinue, onFieldChange }) {
  return (
    <>
      <NoticeStepRail activeStep="write" />
      <section className="platform-notices-flow-grid">
        <div className="platform-notices-panel">
          <header className="platform-notices-panel__heading">
            <h2>Write Notice</h2>
          </header>
          <div className="platform-notices-form">
            <FieldShell label="Title">
              <input
                maxLength={150}
                value={form.title}
                onChange={(event) => onFieldChange('title', event.target.value)}
              />
            </FieldShell>
            <FieldShell label="Message">
              <textarea
                maxLength={4000}
                rows={8}
                value={form.message}
                onChange={(event) => onFieldChange('message', event.target.value)}
              />
              <small>{form.message.length}/4000</small>
            </FieldShell>
          </div>
          <FormErrorMessage className="platform-notices-error">{error}</FormErrorMessage>
          <div className="platform-notices-actions">
            <span />
            <PrimaryButton icon={ChevronRight} onClick={onContinue}>
              Continue
            </PrimaryButton>
          </div>
        </div>
        <NoticePreview message={form.message} title={form.title} />
      </section>
    </>
  )
}

function AudienceChoice({ form, onChange }) {
  const options = [
    {
      description: 'Shown to every currently eligible user.',
      label: 'All eligible users',
      value: AUDIENCE_TYPE_ALL_ELIGIBLE,
    },
    {
      description: `Choose up to ${PLATFORM_NOTICE_SELECTED_USER_LIMIT} users.`,
      label: 'Selected users',
      value: AUDIENCE_TYPE_SELECTED,
    },
  ]

  return (
    <fieldset className="platform-notices-audience">
      <legend>Audience</legend>
      <div className="platform-notices-audience__options">
        {options.map((option) => (
          <button
            aria-pressed={form.audienceType === option.value}
            className={form.audienceType === option.value ? 'is-selected' : ''}
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
          >
            <span aria-hidden="true" />
            <strong>{option.label}</strong>
            <small>{option.description}</small>
          </button>
        ))}
      </div>
    </fieldset>
  )
}

function SelectedUserToken({ onClear, user }) {
  return (
    <div className="platform-notices-user-token">
      <div>
        <strong>{userDisplayName(user)}</strong>
        <span>{user.email || user.id}</span>
      </div>
      <button aria-label="Clear selected user" type="button" onClick={onClear}>
        <X aria-hidden="true" />
      </button>
    </div>
  )
}

function UserSearch({
  error,
  lookupState,
  onAdd,
  onClearCandidate,
  onQueryChange,
  onSelectCandidate,
  query,
  results,
  selectedCandidate,
  selectedUsers,
}) {
  const selectedIds = useMemo(
    () => new Set(selectedUsers.map((user) => user.id)),
    [selectedUsers],
  )
  const isAtSelectedUserLimit = selectedUsers.length >= PLATFORM_NOTICE_SELECTED_USER_LIMIT
  const canAdd = canAddPlatformNoticeSelectedUser(selectedCandidate, selectedUsers)

  return (
    <div className="platform-notices-user-search">
      <span className="platform-notices-label">Find eligible users</span>
      <div className="platform-notices-user-search__row">
        <div className="platform-notices-user-search__field">
          {selectedCandidate ? (
            <SelectedUserToken user={selectedCandidate} onClear={onClearCandidate} />
          ) : (
            <>
              <input
                autoComplete="off"
                placeholder="Search by name, email, or user ID"
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
              />
              {query.trim().length >= USER_SEARCH_MIN_LENGTH && (
                <div className="platform-notices-user-search__menu">
                  {lookupState === 'loading' && <p>Searching...</p>}
                  {lookupState === 'ready' && results.length === 0 && (
                    <p>No eligible users found.</p>
                  )}
                  {lookupState === 'ready' && results.map((user) => {
                    const alreadyAdded = selectedIds.has(user.id)
                    const isDisabled = alreadyAdded || isAtSelectedUserLimit
                    return (
                      <button
                        className={isDisabled ? 'is-disabled' : ''}
                        disabled={isDisabled}
                        key={user.id}
                        type="button"
                        onClick={() => onSelectCandidate(user)}
                      >
                        <span>
                          <strong>{userDisplayName(user)}</strong>
                          <small>{user.email || user.id}</small>
                        </span>
                        {alreadyAdded && <em>Added</em>}
                        {!alreadyAdded && isAtSelectedUserLimit && <em>Max</em>}
                      </button>
                    )
                  })}
                </div>
              )}
            </>
          )}
        </div>
        <PrimaryButton disabled={!canAdd} icon={UserPlus} onClick={onAdd}>
          Add
        </PrimaryButton>
      </div>
      <FormErrorMessage className="platform-notices-error">{error}</FormErrorMessage>
    </div>
  )
}

function AddedRecipients({ onRemove, selectedUsers }) {
  return (
    <section className="platform-notices-added">
      <header>
        <span>Added recipients</span>
        <strong>{selectedUsers.length} / {PLATFORM_NOTICE_SELECTED_USER_LIMIT}</strong>
      </header>
      <div className="platform-notices-added__list">
        {selectedUsers.length === 0 ? (
          <p>No recipients selected.</p>
        ) : (
          selectedUsers.map((user) => (
            <div className="platform-notices-recipient-row" key={user.id}>
              <span>
                <strong>{userDisplayName(user)}</strong>
                <small>{user.email || user.id}</small>
              </span>
              <button
                aria-label={`Remove ${userDisplayName(user)}`}
                type="button"
                onClick={() => onRemove(user.id)}
              >
                <X aria-hidden="true" />
                Remove
              </button>
            </div>
          ))
        )}
      </div>
    </section>
  )
}

function ChooseAudienceStep({
  error,
  form,
  lookupError,
  lookupState,
  onAddSelectedUser,
  onBack,
  onClearCandidate,
  onContinue,
  onFieldChange,
  onQueryChange,
  onRemoveSelectedUser,
  onSelectCandidate,
  query,
  results,
  selectedCandidate,
  selectedUsers,
}) {
  return (
    <>
      <NoticeStepRail activeStep="audience" />
      <section className="platform-notices-panel">
        <header className="platform-notices-panel__heading">
          <h2>Choose Audience</h2>
        </header>
        <AudienceChoice
          form={form}
          onChange={(audienceType) => onFieldChange('audienceType', audienceType)}
        />
        {form.audienceType === AUDIENCE_TYPE_ALL_ELIGIBLE ? (
          <div className="platform-notices-audience-note">
            This notice will remain visible to current and future eligible users until cancelled.
          </div>
        ) : (
          <>
            <UserSearch
              error={lookupError}
              lookupState={lookupState}
              query={query}
              results={results}
              selectedCandidate={selectedCandidate}
              selectedUsers={selectedUsers}
              onAdd={onAddSelectedUser}
              onClearCandidate={onClearCandidate}
              onQueryChange={onQueryChange}
              onSelectCandidate={onSelectCandidate}
            />
            <AddedRecipients
              selectedUsers={selectedUsers}
              onRemove={onRemoveSelectedUser}
            />
          </>
        )}
        <FormErrorMessage className="platform-notices-error">{error}</FormErrorMessage>
        <div className="platform-notices-actions">
          <SecondaryButton icon={ChevronLeft} onClick={onBack}>
            Back
          </SecondaryButton>
          <PrimaryButton icon={Search} onClick={onContinue}>
            Review Notice
          </PrimaryButton>
        </div>
      </section>
    </>
  )
}

function ReviewNoticeStep({
  error,
  form,
  onBack,
  onOpenConfirm,
  selectedUsers,
  submitState,
}) {
  const audienceText = form.audienceType === AUDIENCE_TYPE_ALL_ELIGIBLE
    ? 'All eligible users'
    : `${selectedUsers.length} selected ${selectedUsers.length === 1 ? 'user' : 'users'}`

  return (
    <>
      <NoticeStepRail activeStep="review" />
      <section className="platform-notices-panel">
        <header className="platform-notices-panel__heading">
          <h2>Review Platform Notice</h2>
        </header>
        <div className="platform-notices-review">
          <div className="platform-notices-review__facts">
            <span className="platform-notices-label">Audience</span>
            <strong>{audienceText}</strong>
          </div>
          <div className="platform-notices-review__preview">
            <NoticePreview message={form.message} title={form.title} />
          </div>
        </div>
        <FormErrorMessage className="platform-notices-error">{error}</FormErrorMessage>
        <div className="platform-notices-actions">
          <SecondaryButton disabled={submitState === 'saving'} icon={ChevronLeft} onClick={onBack}>
            Back
          </SecondaryButton>
          <PrimaryButton
            disabled={submitState === 'saving'}
            icon={Send}
            onClick={onOpenConfirm}
          >
            Send Notice
          </PrimaryButton>
        </div>
      </section>
    </>
  )
}

function ConfirmSendModal({ onClose, onSend, submitState }) {
  return (
    <div className="platform-notices-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        aria-labelledby="platform-notices-confirm-title"
        aria-modal="true"
        className="platform-notices-modal"
        role="dialog"
        onClick={(event) => event.stopPropagation()}
      >
        <header>
          <h2 id="platform-notices-confirm-title">
            <span className="platform-notices-modal__icon">
              <Send aria-hidden="true" />
            </span>
            <span>Send platform notice?</span>
          </h2>
          <button aria-label="Close" disabled={submitState === 'saving'} type="button" onClick={onClose}>
            <X aria-hidden="true" />
          </button>
        </header>
        <p className="platform-notices-modal__copy">
          This notice cannot be edited after sending. Cancelling later withdraws it from everyone.
        </p>
        <div className="platform-notices-modal__actions">
          <PrimaryButton disabled={submitState === 'saving'} icon={Send} onClick={onSend}>
            Send Notice
          </PrimaryButton>
        </div>
      </section>
    </div>
  )
}

function CancelNoticeModal({ cancelError, cancelReason, cancelState, onClose, onConfirm, onReasonChange }) {
  return (
    <div className="platform-notices-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        aria-labelledby="platform-notices-cancel-title"
        aria-modal="true"
        className="platform-notices-modal"
        role="dialog"
        onClick={(event) => event.stopPropagation()}
      >
        <header>
          <h2 id="platform-notices-cancel-title">Cancel platform notice?</h2>
          <button aria-label="Close" disabled={cancelState === 'saving'} type="button" onClick={onClose}>
            <X aria-hidden="true" />
          </button>
        </header>
        <FieldShell label="Cancellation reason">
          <textarea
            maxLength={1000}
            rows={4}
            value={cancelReason}
            onChange={(event) => onReasonChange(event.target.value)}
          />
          <small>{cancelReason.length}/1000</small>
        </FieldShell>
        <FormErrorMessage className="platform-notices-error">{cancelError}</FormErrorMessage>
        <div className="platform-notices-modal__actions">
          <SecondaryButton disabled={cancelState === 'saving'} onClick={onClose}>
            Back
          </SecondaryButton>
          <button
            className="platform-notices-button platform-notices-button--danger"
            disabled={cancelState === 'saving'}
            type="button"
            onClick={onConfirm}
          >
            Cancel Notice
          </button>
        </div>
      </section>
    </div>
  )
}

function HistoryLoading() {
  return (
    <div className="platform-notices-history-list" role="status">
      {Array.from({ length: 4 }).map((_, index) => (
        <div className="platform-notices-history-row" key={index}>
          <SkeletonBlock height="0.92rem" rounded width="48%" />
          <SkeletonBlock height="0.72rem" rounded width="64%" />
        </div>
      ))}
    </div>
  )
}

function NoticeStatus({ notice }) {
  const status = platformNoticeStatusLabel(notice)

  return (
    <span className={`platform-notices-status platform-notices-status--${status.toLowerCase()}`}>
      {status}
    </span>
  )
}

function HistoryRow({ notice, onSelect }) {
  return (
    <button
      className="platform-notices-history-row"
      type="button"
      onClick={() => onSelect(notice.id)}
    >
      <span className="platform-notices-history-row__icon" aria-hidden="true">
        <Megaphone />
      </span>
      <span className="platform-notices-history-row__main">
        <strong>{notice.title}</strong>
        <span>{platformNoticeAudienceLabel(notice)} - {formatPlatformNoticeDateTime(notice.published_at)}</span>
      </span>
      <NoticeStatus notice={notice} />
    </button>
  )
}

function HistoryView({
  error,
  filters,
  hasMore,
  isLoadingMore,
  isSearchBelowMinimum,
  loadState,
  notices,
  onFilterChange,
  onLoadMore,
  onRefresh,
  onSelect,
}) {
  return (
    <section className="platform-notices-panel">
      <header className="platform-notices-panel__heading platform-notices-panel__heading--inline">
        <div>
          <h2>History</h2>
        </div>
        <button aria-label="Refresh notices" className="platform-notices-icon-button" type="button" onClick={onRefresh}>
          <RefreshCw aria-hidden="true" />
        </button>
      </header>
      <div className="platform-notices-filters">
        <input
          maxLength={PLATFORM_NOTICE_HISTORY_SEARCH_MAX_LENGTH}
          placeholder="Search title or message"
          value={filters.search}
          onChange={(event) => onFilterChange('search', event.target.value)}
        />
        <select
          value={filters.status}
          onChange={(event) => onFilterChange('status', event.target.value)}
        >
          {PLATFORM_NOTICE_STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </div>
      {loadState === 'loading' ? (
        <HistoryLoading />
      ) : loadState === 'error' ? (
        <div className="platform-notices-empty platform-notices-empty--error">
          <Megaphone aria-hidden="true" />
          <strong>Platform notices could not be loaded</strong>
          <p>{error || 'Try refreshing the list.'}</p>
          <SecondaryButton icon={RefreshCw} onClick={onRefresh}>Retry</SecondaryButton>
        </div>
      ) : isSearchBelowMinimum ? (
        <div className="platform-notices-empty">
          <Search aria-hidden="true" />
          <strong>Keep typing</strong>
          <p>Type at least 3 letters or numbers to search history.</p>
        </div>
      ) : notices.length === 0 ? (
        <div className="platform-notices-empty">
          <Megaphone aria-hidden="true" />
          <strong>No platform notices yet</strong>
        </div>
      ) : (
        <div className="platform-notices-history-list">
          {notices.map((notice) => (
            <HistoryRow key={notice.id} notice={notice} onSelect={onSelect} />
          ))}
        </div>
      )}
      {loadState === 'ready' && error && (
        <FormErrorMessage className="platform-notices-error">
          {error}
        </FormErrorMessage>
      )}
      {hasMore && (
        <div className="platform-notices-load-more">
          <SecondaryButton disabled={isLoadingMore} onClick={onLoadMore}>
            {isLoadingMore ? 'Loading...' : 'Load More'}
          </SecondaryButton>
        </div>
      )}
    </section>
  )
}

function RecipientRows({ hasMore, loadMore, recipients }) {
  return (
    <section className="platform-notices-detail-section">
      <header>
        <span>Selected recipients</span>
      </header>
      <div className="platform-notices-detail-recipients">
        {recipients.length === 0 ? (
          <p>No recipients loaded.</p>
        ) : (
          recipients.map((recipient) => (
            <div className="platform-notices-recipient-row" key={recipient.user_id}>
              <span>
                <strong>{recipient.display_name}</strong>
                <small>{recipient.email || recipient.user_id}</small>
              </span>
              <em>{recipient.read_at ? 'Read' : 'Unread'}</em>
            </div>
          ))
        )}
      </div>
      {hasMore && (
        <div className="platform-notices-load-more">
          <SecondaryButton onClick={loadMore}>Load More</SecondaryButton>
        </div>
      )}
    </section>
  )
}

function NoticeDetail({
  cancelError,
  cancelReason,
  cancelState,
  detailError,
  detailState,
  hasMoreRecipients,
  notice,
  onBack,
  onCancelNotice,
  onCloseCancel,
  onLoadMoreRecipients,
  onOpenCancel,
  onReasonChange,
  onRetry,
  recipients,
  showCancelModal,
}) {
  if (detailState === 'error') {
    return (
      <section className="platform-notices-panel">
        <button className="platform-notices-button platform-notices-detail-back" type="button" onClick={onBack}>
          <ChevronLeft aria-hidden="true" />
          Back
        </button>
        <div className="platform-notices-empty platform-notices-empty--error">
          <Megaphone aria-hidden="true" />
          <strong>Platform notice could not be loaded</strong>
          <p>{detailError || 'Try opening the notice again.'}</p>
          <SecondaryButton icon={RefreshCw} onClick={onRetry}>Retry</SecondaryButton>
        </div>
      </section>
    )
  }

  if (detailState === 'loading' || !notice) {
    return (
      <section className="platform-notices-panel">
        <SkeletonBlock height="1.4rem" rounded width="40%" />
        <SkeletonBlock height="10rem" rounded width="100%" />
      </section>
    )
  }

  return (
    <>
      <section className="platform-notices-panel">
        <button className="platform-notices-button platform-notices-detail-back" type="button" onClick={onBack}>
          <ChevronLeft aria-hidden="true" />
          Back
        </button>
        <header className="platform-notices-detail-header">
          <span className="platform-notices-detail-header__icon" aria-hidden="true">
            <Megaphone />
          </span>
          <div>
            <h2>{notice.title}</h2>
            <p>Published {formatPlatformNoticeDateTime(notice.published_at)}</p>
          </div>
          <NoticeStatus notice={notice} />
        </header>
        <div className="platform-notices-detail-grid">
          <NoticePreview message={notice.message} title={notice.title} />
          <section className="platform-notices-detail-section">
            <header>
              <span>Audience</span>
            </header>
            <strong>{platformNoticeAudienceLabel(notice)}</strong>
            {notice.cancelled_at && (
              <div className="platform-notices-cancelled-note">
                <span>Cancelled</span>
                <p>{formatPlatformNoticeDateTime(notice.cancelled_at)}</p>
                <p>{notice.cancellation_reason}</p>
              </div>
            )}
            {!notice.cancelled_at && (
              <button
                className="platform-notices-button platform-notices-button--danger"
                type="button"
                onClick={onOpenCancel}
              >
                Cancel Notice
              </button>
            )}
          </section>
        </div>
        {notice.audience_type === AUDIENCE_TYPE_SELECTED && (
          <RecipientRows
            hasMore={hasMoreRecipients}
            recipients={recipients}
            loadMore={onLoadMoreRecipients}
          />
        )}
      </section>
      {showCancelModal && (
        <CancelNoticeModal
          cancelError={cancelError}
          cancelReason={cancelReason}
          cancelState={cancelState}
          onClose={onCloseCancel}
          onConfirm={onCancelNotice}
          onReasonChange={onReasonChange}
        />
      )}
    </>
  )
}

function AdminPlatformNoticesPage() {
  const { currentUser } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const { noticeId } = useParams()
  const isCreateRoute = location.pathname.endsWith('/platform-notices/new')
  const activeMode = isCreateRoute ? 'create' : 'history'
  const [filters, setFilters] = useState(EMPTY_PLATFORM_NOTICE_FILTERS)
  const [form, setForm] = useState(EMPTY_PLATFORM_NOTICE_FORM)
  const [selectedUsers, setSelectedUsers] = useState([])
  const [activeStep, setActiveStep] = useState('write')
  const [stepError, setStepError] = useState('')
  const [submitState, setSubmitState] = useState('idle')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [notices, setNotices] = useState([])
  const [historyState, setHistoryState] = useState('idle')
  const [historyError, setHistoryError] = useState('')
  const [historyCursor, setHistoryCursor] = useState('')
  const [historyHasMore, setHistoryHasMore] = useState(false)
  const [historyLoadingMore, setHistoryLoadingMore] = useState(false)
  const [historyReloadKey, setHistoryReloadKey] = useState(0)
  const [notice, setNotice] = useState(null)
  const [detailState, setDetailState] = useState('idle')
  const [detailError, setDetailError] = useState('')
  const [detailReloadKey, setDetailReloadKey] = useState(0)
  const [recipients, setRecipients] = useState([])
  const [recipientCursor, setRecipientCursor] = useState('')
  const [recipientHasMore, setRecipientHasMore] = useState(false)
  const [cancelOpen, setCancelOpen] = useState(false)
  const [cancelReason, setCancelReason] = useState('')
  const [cancelError, setCancelError] = useState('')
  const [cancelState, setCancelState] = useState('idle')
  const [userQuery, setUserQuery] = useState('')
  const [userResults, setUserResults] = useState([])
  const [userLookupState, setUserLookupState] = useState('idle')
  const [userLookupError, setUserLookupError] = useState('')
  const [selectedCandidate, setSelectedCandidate] = useState(null)
  const historyAbortControllerRef = useRef(null)
  const historyRequestIdRef = useRef(0)
  const publishKeyRef = useRef(createPlatformNoticeIdempotencyKey())
  const debouncedHistorySearch = useDebouncedValue(
    filters.search,
    HISTORY_SEARCH_DEBOUNCE_MS,
  )
  const activeHistorySearch = getActivePlatformNoticeHistorySearch(
    debouncedHistorySearch,
    PLATFORM_NOTICE_HISTORY_SEARCH_MIN_MEANINGFUL_CHARS,
  )
  const immediateActiveHistorySearch = getActivePlatformNoticeHistorySearch(
    filters.search,
    PLATFORM_NOTICE_HISTORY_SEARCH_MIN_MEANINGFUL_CHARS,
  )
  const hasHistorySearchInput = Boolean(filters.search.trim())
  const isHistorySearchBelowMinimum =
    hasHistorySearchInput && !immediateActiveHistorySearch
  const isHistorySearchWaitingForDebounce = Boolean(
    immediateActiveHistorySearch
    && immediateActiveHistorySearch !== activeHistorySearch,
  )

  useEffect(() => {
    if (!currentUser || noticeId || isCreateRoute) {
      return undefined
    }

    if (isHistorySearchBelowMinimum) {
      historyRequestIdRef.current += 1
      historyAbortControllerRef.current?.abort()
      historyAbortControllerRef.current = null
      setHistoryState('ready')
      setHistoryLoadingMore(false)
      setHistoryError('')
      setNotices([])
      setHistoryCursor('')
      setHistoryHasMore(false)
      return undefined
    }

    if (isHistorySearchWaitingForDebounce) {
      historyRequestIdRef.current += 1
      historyAbortControllerRef.current?.abort()
      historyAbortControllerRef.current = null
      setHistoryState('loading')
      setHistoryLoadingMore(false)
      setHistoryError('')
      setNotices([])
      setHistoryCursor('')
      setHistoryHasMore(false)
      return undefined
    }

    let isMounted = true
    const requestId = historyRequestIdRef.current + 1
    const controller = new AbortController()
    historyRequestIdRef.current = requestId
    historyAbortControllerRef.current?.abort()
    historyAbortControllerRef.current = controller

    setHistoryState('loading')
    setHistoryLoadingMore(false)
    setHistoryError('')
    setNotices([])
    setHistoryCursor('')
    setHistoryHasMore(false)

    listPlatformNotices({
      firebaseUser: currentUser,
      limit: HISTORY_LIMIT,
      search: activeHistorySearch,
      signal: controller.signal,
      status: filters.status,
    })
      .then((response) => {
        if (!isMounted || requestId !== historyRequestIdRef.current) {
          return
        }
        setNotices(response.notices || [])
        setHistoryCursor(response.next_cursor || '')
        setHistoryHasMore(Boolean(response.has_more))
        setHistoryState('ready')
        setHistoryError('')
      })
      .catch((error) => {
        if (
          !isMounted
          || requestId !== historyRequestIdRef.current
          || error.name === 'AbortError'
        ) {
          return
        }
        setHistoryState('error')
        setHistoryError(error.message || 'Platform notices could not be loaded.')
        setNotices([])
        setHistoryCursor('')
        setHistoryHasMore(false)
      })

    return () => {
      isMounted = false
      controller.abort()
      if (historyAbortControllerRef.current === controller) {
        historyAbortControllerRef.current = null
      }
    }
  }, [
    activeHistorySearch,
    currentUser,
    debouncedHistorySearch,
    filters.search,
    filters.status,
    historyReloadKey,
    isHistorySearchBelowMinimum,
    isHistorySearchWaitingForDebounce,
    isCreateRoute,
    noticeId,
  ])

  useEffect(() => {
    if (!currentUser || !noticeId) {
      return undefined
    }

    let isMounted = true

    Promise.resolve()
      .then(() => {
        if (!isMounted) {
          return null
        }
        setDetailState('loading')
        setDetailError('')
        setNotice(null)
        setRecipients([])
        setRecipientCursor('')
        setRecipientHasMore(false)
        return getPlatformNotice({ firebaseUser: currentUser, noticeId })
      })
      .then((response) => {
        if (!isMounted || !response) {
          return null
        }
        setNotice(response)
        setDetailState('ready')
        setDetailError('')
        if (response.audience_type === AUDIENCE_TYPE_SELECTED) {
          return listPlatformNoticeRecipients({
            firebaseUser: currentUser,
            limit: RECIPIENT_LIMIT,
            noticeId,
          })
        }
        return null
      })
      .then((response) => {
        if (!isMounted || !response) {
          return
        }
        setRecipients(response.recipients || [])
        setRecipientCursor(response.next_cursor || '')
        setRecipientHasMore(Boolean(response.has_more))
      })
      .catch((error) => {
        if (!isMounted) {
          return
        }
        setNotice(null)
        setRecipients([])
        setRecipientCursor('')
        setRecipientHasMore(false)
        setDetailState('error')
        setDetailError(error.message || 'Platform notice could not be loaded.')
      })

    return () => {
      isMounted = false
    }
  }, [currentUser, detailReloadKey, noticeId])

  useEffect(() => {
    if (!currentUser || !isCreateRoute || form.audienceType !== AUDIENCE_TYPE_SELECTED) {
      return undefined
    }

    const normalizedQuery = userQuery.trim()
    if (selectedCandidate || normalizedQuery.length < USER_SEARCH_MIN_LENGTH) {
      return undefined
    }

    let isMounted = true
    const controller = new AbortController()
    const timeoutId = window.setTimeout(() => {
      setUserLookupState('loading')
      setUserLookupError('')
      listAdminLookupUsers({
        accountStatus: 'active',
        firebaseUser: currentUser,
        limit: USER_LOOKUP_LIMIT,
        query: normalizedQuery,
        signal: controller.signal,
      })
        .then((results) => {
          if (!isMounted) {
            return
          }
          setUserResults(results.filter((user) => user.eligible !== false))
          setUserLookupState('ready')
        })
        .catch((error) => {
          if (!isMounted || error.name === 'AbortError') {
            return
          }
          setUserResults([])
          setUserLookupState('error')
          setUserLookupError(error.message || 'User search failed.')
        })
    }, USER_SEARCH_DEBOUNCE_MS)

    return () => {
      isMounted = false
      controller.abort()
      window.clearTimeout(timeoutId)
    }
  }, [currentUser, form.audienceType, isCreateRoute, selectedCandidate, userQuery])

  function resetCreateFlow() {
    setForm(EMPTY_PLATFORM_NOTICE_FORM)
    setSelectedUsers([])
    setActiveStep('write')
    setStepError('')
    setSubmitState('idle')
    setConfirmOpen(false)
    setUserQuery('')
    setUserResults([])
    setUserLookupState('idle')
    setUserLookupError('')
    setSelectedCandidate(null)
    publishKeyRef.current = createPlatformNoticeIdempotencyKey()
  }

  function prepareHistoryLoad() {
    historyRequestIdRef.current += 1
    historyAbortControllerRef.current?.abort()
    setHistoryState('loading')
    setHistoryLoadingMore(false)
    setHistoryError('')
    setNotices([])
    setHistoryCursor('')
    setHistoryHasMore(false)
  }

  function handleTabChange(mode) {
    setStepError('')
    if (mode === 'create') {
      resetCreateFlow()
      navigate('/admin/platform-notices/new')
    } else {
      navigate('/admin/platform-notices')
    }
  }

  function updateFormField(field, value) {
    setStepError('')
    setForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }))
    if (field === 'audienceType') {
      setSelectedCandidate(null)
      setUserQuery('')
      setUserResults([])
      setUserLookupState('idle')
      setUserLookupError('')
    }
  }

  function continueFromWrite() {
    const error = validatePlatformNoticeContent(form)
    if (error) {
      setStepError(error)
      return
    }
    setStepError('')
    setActiveStep('audience')
  }

  function continueFromAudience() {
    const error = validatePlatformNoticeAudience(form, selectedUsers)
    if (error) {
      setStepError(error)
      return
    }
    setStepError('')
    setActiveStep('review')
  }

  function addSelectedUser() {
    if (!selectedCandidate) {
      return
    }
    if (selectedUsers.some((user) => user.id === selectedCandidate.id)) {
      setSelectedCandidate(null)
      setUserQuery('')
      return
    }
    if (selectedUsers.length >= PLATFORM_NOTICE_SELECTED_USER_LIMIT) {
      setUserLookupError(`Selected notices cannot include more than ${PLATFORM_NOTICE_SELECTED_USER_LIMIT} users.`)
      return
    }
    setSelectedUsers((currentUsers) => [...currentUsers, selectedCandidate])
    setSelectedCandidate(null)
    setUserQuery('')
    setUserResults([])
    setUserLookupState('idle')
    setUserLookupError('')
  }

  function removeSelectedUser(userId) {
    setSelectedUsers((currentUsers) => currentUsers.filter((user) => user.id !== userId))
  }

  async function sendNotice() {
    const contentError = validatePlatformNoticeContent(form)
    const audienceError = validatePlatformNoticeAudience(form, selectedUsers)
    if (contentError || audienceError) {
      setConfirmOpen(false)
      setStepError(contentError || audienceError)
      return
    }

    setSubmitState('saving')
    setStepError('')
    try {
      const response = await createPlatformNotice({
        firebaseUser: currentUser,
        payload: buildPlatformNoticeCreatePayload({
          form,
          idempotencyKey: publishKeyRef.current,
          selectedUsers,
        }),
      })
      resetCreateFlow()
      navigate(`/admin/platform-notices/${response.notice.id}`)
    } catch (error) {
      setConfirmOpen(false)
      setSubmitState('idle')
      setStepError(error.message || 'Platform notice could not be sent.')
    }
  }

  async function loadMoreHistory() {
    if (!currentUser || !historyCursor || historyLoadingMore) {
      return
    }

    const requestId = historyRequestIdRef.current
    setHistoryLoadingMore(true)
    setHistoryError('')

    try {
      const response = await listPlatformNotices({
        cursor: historyCursor,
        firebaseUser: currentUser,
        limit: HISTORY_LIMIT,
        search: activeHistorySearch,
        status: filters.status,
      })
      if (requestId !== historyRequestIdRef.current) {
        return
      }
      setNotices((currentNotices) => [
        ...currentNotices,
        ...(response.notices || []),
      ])
      setHistoryCursor(response.next_cursor || '')
      setHistoryHasMore(Boolean(response.has_more))
    } catch (error) {
      if (requestId !== historyRequestIdRef.current) {
        return
      }
      setHistoryError(error.message || 'More platform notices could not be loaded.')
    } finally {
      if (requestId === historyRequestIdRef.current) {
        setHistoryLoadingMore(false)
      }
    }
  }

  async function loadMoreRecipients() {
    if (!currentUser || !noticeId || !recipientCursor) {
      return
    }
    const response = await listPlatformNoticeRecipients({
      cursor: recipientCursor,
      firebaseUser: currentUser,
      limit: RECIPIENT_LIMIT,
      noticeId,
    })
    setRecipients((currentRecipients) => [
      ...currentRecipients,
      ...(response.recipients || []),
    ])
    setRecipientCursor(response.next_cursor || '')
    setRecipientHasMore(Boolean(response.has_more))
  }

  async function cancelNotice() {
    const reason = cancelReason.trim()
    if (!reason) {
      setCancelError('Enter cancellation reason.')
      return
    }

    setCancelState('saving')
    setCancelError('')
    try {
      const response = await cancelPlatformNotice({
        firebaseUser: currentUser,
        noticeId,
        payload: buildPlatformNoticeCancelPayload(reason),
      })
      setNotice(response)
      setCancelOpen(false)
      setCancelReason('')
      setCancelState('idle')
    } catch (error) {
      setCancelState('idle')
      setCancelError(error.message || 'Platform notice could not be cancelled.')
    }
  }

  function refreshHistory() {
    prepareHistoryLoad()
    setHistoryReloadKey((currentKey) => currentKey + 1)
  }

  function renderCreateFlow() {
    if (activeStep === 'write') {
      return (
        <WriteNoticeStep
          error={stepError}
          form={form}
          onContinue={continueFromWrite}
          onFieldChange={updateFormField}
        />
      )
    }

    if (activeStep === 'audience') {
      return (
        <ChooseAudienceStep
          error={stepError}
          form={form}
          lookupError={userLookupError}
          lookupState={userLookupState}
          query={userQuery}
          results={userResults}
          selectedCandidate={selectedCandidate}
          selectedUsers={selectedUsers}
          onAddSelectedUser={addSelectedUser}
          onBack={() => {
            setStepError('')
            setActiveStep('write')
          }}
          onClearCandidate={() => {
            setSelectedCandidate(null)
            setUserQuery('')
            setUserResults([])
            setUserLookupError('')
            setUserLookupState('idle')
          }}
          onContinue={continueFromAudience}
          onFieldChange={updateFormField}
          onQueryChange={(value) => {
            setUserQuery(value)
            setSelectedCandidate(null)
            setUserLookupError('')
            if (value.trim().length < USER_SEARCH_MIN_LENGTH) {
              setUserResults([])
              setUserLookupState('idle')
            }
          }}
          onRemoveSelectedUser={removeSelectedUser}
          onSelectCandidate={(user) => {
            setSelectedCandidate(user)
            setUserResults([])
            setUserQuery(userDisplayName(user))
          }}
        />
      )
    }

    return (
      <>
        <ReviewNoticeStep
          error={stepError}
          form={form}
          selectedUsers={selectedUsers}
          submitState={submitState}
          onBack={() => {
            setStepError('')
            setActiveStep('audience')
          }}
          onOpenConfirm={() => setConfirmOpen(true)}
        />
        {confirmOpen && (
          <ConfirmSendModal
            submitState={submitState}
            onClose={() => setConfirmOpen(false)}
            onSend={sendNotice}
          />
        )}
      </>
    )
  }

  return (
    <AdminWorkspaceLayout
      description="Create, send, and monitor platform notices."
      icon={Megaphone}
      title="Platform Notices"
    >
      <div className="platform-notices">
        <PageTabs activeMode={activeMode} onChange={handleTabChange} />
        {isCreateRoute && renderCreateFlow()}
        {!isCreateRoute && !noticeId && (
          <HistoryView
            error={historyError}
            filters={filters}
            hasMore={historyHasMore}
            isLoadingMore={historyLoadingMore}
            isSearchBelowMinimum={isHistorySearchBelowMinimum}
            loadState={historyState}
            notices={notices}
            onFilterChange={(field, value) => {
              setStepError('')
              prepareHistoryLoad()
              setFilters((currentFilters) => ({
                ...currentFilters,
                [field]: field === 'search'
                  ? value.slice(0, PLATFORM_NOTICE_HISTORY_SEARCH_MAX_LENGTH)
                  : value,
              }))
            }}
            onLoadMore={loadMoreHistory}
            onRefresh={refreshHistory}
            onSelect={(id) => navigate(`/admin/platform-notices/${id}`)}
          />
        )}
        {!isCreateRoute && noticeId && (
          <NoticeDetail
            cancelError={cancelError}
            cancelReason={cancelReason}
            cancelState={cancelState}
            detailError={detailError}
            detailState={detailState}
            hasMoreRecipients={recipientHasMore}
            notice={notice}
            recipients={recipients}
            showCancelModal={cancelOpen}
            onBack={() => navigate('/admin/platform-notices')}
            onCancelNotice={cancelNotice}
            onCloseCancel={() => setCancelOpen(false)}
            onLoadMoreRecipients={loadMoreRecipients}
            onOpenCancel={() => {
              setCancelError('')
              setCancelOpen(true)
            }}
            onReasonChange={(value) => {
              setCancelReason(value)
              setCancelError('')
            }}
            onRetry={() => setDetailReloadKey((currentKey) => currentKey + 1)}
          />
        )}
      </div>
    </AdminWorkspaceLayout>
  )
}

export default AdminPlatformNoticesPage
