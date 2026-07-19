import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  CheckCircle2,
  ClipboardList,
  FileClock,
  Link2,
  MessageSquareText,
  PenLine,
  X,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminReviewCases.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import {
  addAdminReviewCaseNote,
  getAdminReviewCase,
  closeAdminReviewCase,
} from '../shared/adminApi.js'
import {
  canOpenAdminReviewTarget,
  formatAdminReviewDateTime,
  formatAdminReviewIssueLabel,
  formatAdminReviewStatus,
  formatAdminReviewTargetCurrentStatus,
  formatAdminReviewTargetType,
  getAdminReviewTargetPath,
  shortAdminReviewId,
} from './adminReviewFormatters.js'

const NOTE_MAX_LENGTH = 1000
const NOTE_CASE_LIMIT = 100
const REASON_MAX_LENGTH = 2000
const CLOSURE_OUTCOMES = [
  { label: 'Enforcement applied', value: 'enforcement_applied' },
  { label: 'No action needed', value: 'no_action_needed' },
  { label: 'Invalid signal', value: 'invalid_signal' },
]

function createReviewIdempotencyKey(prefix, reviewCaseId) {
  const suffix = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`
  return `${prefix}:${reviewCaseId}:${suffix}`
}

function ReviewSection({ children, className = '', count, countText, icon: Icon, title }) {
  const sectionClassName = [
    'admin-review-panel',
    className,
  ].filter(Boolean).join(' ')

  return (
    <section className={sectionClassName}>
      <div className="admin-review-panel__heading">
        <div>
          <Icon />
          <h2>{title}</h2>
        </div>
        {count !== undefined && (
          <span className="admin-review-panel__count">
            {countText || count}
          </span>
        )}
      </div>
      {children}
    </section>
  )
}

function ReviewField({ label, value }) {
  return (
    <div className="admin-review-field">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function getOpenTargetLabel(reviewCase) {
  if (reviewCase.target_sub_post_id || reviewCase.target_sub_post_request_id) {
    return 'Open post'
  }
  if (reviewCase.target_game_id) {
    return 'Open game'
  }
  return 'Open record'
}

function ReviewCaseOverview({ reviewCase, targetPath }) {
  const targetStatus = formatAdminReviewTargetCurrentStatus(reviewCase)

  return (
    <section className="admin-review-panel admin-review-overview">
      <div className="admin-review-overview__heading">
        <div>
          <ClipboardList />
          <h2>Case summary</h2>
        </div>
        {targetPath && (
          <Link className="admin-review-button" to={targetPath}>
            <Link2 />
            {getOpenTargetLabel(reviewCase)}
          </Link>
        )}
      </div>
      <div className="admin-review-overview__facts">
        <ReviewField
          label="Case type"
          value={formatAdminReviewTargetType(reviewCase)}
        />
        <ReviewField
          label="Case status"
          value={formatAdminReviewStatus(reviewCase.case_status)}
        />
        <ReviewField
          label="Content status"
          value={targetStatus || 'Unknown'}
        />
        <ReviewField
          label="Updated"
          value={formatAdminReviewDateTime(reviewCase.updated_at)}
        />
      </div>
    </section>
  )
}

function ClosedReviewSummary({ reviewCase }) {
  return (
    <div className="admin-review-close-summary">
      <ReviewField
        label="Closure outcome"
        value={formatAdminReviewStatus(reviewCase.closure_outcome)}
      />
      <ReviewField
        label="Closure reason"
        value={reviewCase.closure_reason || 'No closure reason recorded.'}
      />
      <ReviewField
        label="Closed"
        value={formatAdminReviewDateTime(reviewCase.closed_at)}
      />
    </div>
  )
}

const TIMELINE_EVENT_PRIORITY = {
  case_created: 0,
  signal_attached: 1,
  finding_attached: 2,
  finding_cleared: 3,
  note_added: 4,
  enforcement_action_linked: 5,
  closed: 6,
}

function getTimelineEventTime(item) {
  const timestamp = new Date(item.created_at).getTime()
  return Number.isNaN(timestamp) ? 0 : timestamp
}

function getTimelineEventPriority(item) {
  return TIMELINE_EVENT_PRIORITY[item.event_type] ?? 99
}

function sortTimelineEvents(items) {
  return [...items].sort((first, second) => {
    const firstTime = getTimelineEventTime(first)
    const secondTime = getTimelineEventTime(second)
    if (firstTime !== secondTime) return firstTime - secondTime

    const firstPriority = getTimelineEventPriority(first)
    const secondPriority = getTimelineEventPriority(second)
    if (firstPriority !== secondPriority) return firstPriority - secondPriority

    return String(first.id).localeCompare(String(second.id))
  })
}

function buildFindingById(findings = []) {
  return new Map(findings.map((finding) => [String(finding.id), finding]))
}

function getTimelineFindingType(item, findingById) {
  const finding = item.content_moderation_finding_id
    ? findingById.get(String(item.content_moderation_finding_id))
    : null

  return finding?.finding_type || item.event_metadata?.finding_type || ''
}

function formatTimelineEventTitle(item, findingById) {
  const findingType = getTimelineFindingType(item, findingById)
  const findingLabel = findingType
    ? formatAdminReviewIssueLabel(findingType)
    : 'Finding'

  switch (item.event_type) {
    case 'case_created':
      return 'Case opened'
    case 'finding_attached':
      return `${findingLabel} added`
    case 'finding_cleared':
      return `${findingLabel} cleared`
    case 'note_added':
      return 'Internal note added'
    case 'closed':
      return 'Case closed'
    case 'enforcement_action_linked':
      return item.event_metadata?.action_type
        ? `${formatAdminReviewStatus(item.event_metadata.action_type)} linked`
        : 'Enforcement action linked'
    case 'signal_attached':
      return item.event_metadata?.source
        ? `${formatAdminReviewStatus(item.event_metadata.source)} signal added`
        : 'Signal added'
    default:
      return formatAdminReviewStatus(item.event_type)
  }
}

function ReviewTimelineRows({ findings, items }) {
  if (!items.length) {
    return <p className="admin-review-empty">No timeline entries.</p>
  }

  const findingById = buildFindingById(findings)
  const timelineItems = sortTimelineEvents(items)

  return (
    <div className="admin-review-timeline">
      {timelineItems.map((item) => (
        <div className="admin-review-timeline-row" key={item.id}>
          <strong>{formatTimelineEventTitle(item, findingById)}</strong>
          <time dateTime={item.created_at}>
            {formatAdminReviewDateTime(item.created_at)}
          </time>
        </div>
      ))}
    </div>
  )
}

function getFindingUpdatedAt(finding) {
  return finding.updated_at || finding.last_detected_at || finding.created_at || ''
}

function formatFindingUpdatedAt(finding) {
  const updatedAt = getFindingUpdatedAt(finding)
  if (!updatedAt) return ''
  return formatAdminReviewDateTime(updatedAt)
}

function ContentModerationFindingRows({ findings }) {
  if (!findings.length) {
    return <p className="admin-review-empty">No findings.</p>
  }

  return (
    <div className="admin-review-list admin-review-list--compact">
      {findings.map((finding) => {
        const updatedAt = formatFindingUpdatedAt(finding)
        const evidence = Array.isArray(finding.evidence) ? finding.evidence : []
        return (
          <article className="admin-review-finding-row" key={finding.id}>
            <div className="admin-review-finding-row__summary">
              <strong>{formatAdminReviewIssueLabel(finding.finding_type)}</strong>
            </div>
            {evidence.length > 0 && (
              <div className="admin-review-finding-row__evidence-block">
                <span className="admin-review-finding-row__evidence-label">Evidence</span>
                <div className="admin-review-finding-row__evidence">
                  {evidence.map((item, index) => (
                    <p
                      className="admin-review-finding-row__excerpt"
                      key={`${finding.id}-${item.start}-${item.end}-${index}`}
                    >
                      {item.display_text}
                    </p>
                  ))}
                </div>
              </div>
            )}
            {updatedAt && (
              <p className="admin-review-finding-row__updated">
                Updated{' '}
                <time dateTime={getFindingUpdatedAt(finding)}>{updatedAt}</time>
              </p>
            )}
          </article>
        )
      })}
    </div>
  )
}

function isCurrentFinding(finding) {
  return finding.current_match !== false
}

function splitReviewFindings(findings = []) {
  return findings.reduce(
    (groups, finding) => {
      if (isCurrentFinding(finding)) {
        groups.current.push(finding)
      } else {
        groups.previous.push(finding)
      }
      return groups
    },
    { current: [], previous: [] },
  )
}

function formatNoteCount(count) {
  return `${count} ${count === 1 ? 'note' : 'notes'}`
}

function sortNotesNewestFirst(notes = []) {
  return [...notes].sort((first, second) => {
    const firstTime = new Date(first.created_at).getTime()
    const secondTime = new Date(second.created_at).getTime()
    if (firstTime !== secondTime) return secondTime - firstTime
    return String(second.id).localeCompare(String(first.id))
  })
}

function formatReviewNoteAuthor(note) {
  if (note.author_display_name) return note.author_display_name
  return `Admin ${shortAdminReviewId(note.author_user_id)}`
}

function ReviewNoteCard({ note, preview = false }) {
  return (
    <article className={`admin-review-note${preview ? ' admin-review-note--preview' : ''}`}>
      <div className="admin-review-note__meta">
        <span>{formatReviewNoteAuthor(note)}</span>
        <span>{formatAdminReviewDateTime(note.created_at)}</span>
      </div>
      <p>{note.body}</p>
    </article>
  )
}

function ReviewNotesModal({ notes, onClose }) {
  const orderedNotes = sortNotesNewestFirst(notes)

  return (
    <div className="admin-review-modal-backdrop">
      <section
        aria-labelledby="admin-review-notes-modal-title"
        aria-modal="true"
        className="admin-review-notes-modal"
        role="dialog"
      >
        <header className="admin-review-notes-modal__header">
          <div>
            <span className="admin-review-notes-modal__icon">
              <MessageSquareText />
            </span>
            <h2 id="admin-review-notes-modal-title">
              Internal Notes · {formatNoteCount(orderedNotes.length)}
            </h2>
          </div>
          <button
            aria-label="Close notes"
            className="admin-review-notes-modal__close"
            type="button"
            onClick={onClose}
          >
            <X />
          </button>
        </header>
        <div className="admin-review-notes-modal__body pl-scrollbar pl-scrollbar--stable">
          {orderedNotes.map((note) => (
            <ReviewNoteCard key={note.id} note={note} />
          ))}
        </div>
      </section>
    </div>
  )
}

function ReviewNotesPanel({
  canAddNote,
  className = '',
  isSubmitting,
  noteBody,
  notes,
  onAddNote,
  onNoteChange,
  onOpenHistory,
}) {
  const orderedNotes = sortNotesNewestFirst(notes)
  const latestNote = orderedNotes[0]
  const noteCount = orderedNotes.length
  const isAtNoteLimit = noteCount >= NOTE_CASE_LIMIT
  const canOpenHistory = noteCount > 0
  const panelClassName = [
    'admin-review-panel',
    'admin-review-notes-panel',
    className,
  ].filter(Boolean).join(' ')

  return (
    <section className={panelClassName}>
      <div className="admin-review-panel__heading admin-review-notes-panel__heading">
        <div>
          <MessageSquareText />
          <h2>Internal Notes</h2>
        </div>
        <span>{formatNoteCount(noteCount)}</span>
      </div>

      <div className="admin-review-notes-preview">
        {latestNote ? (
          <ReviewNoteCard note={latestNote} preview />
        ) : (
          <p className="admin-review-notes-empty">No internal notes yet.</p>
        )}
        <button
          className="admin-review-button admin-review-notes-preview__history"
          disabled={!canOpenHistory}
          type="button"
          onClick={onOpenHistory}
        >
          View All Notes
        </button>
      </div>

      {canAddNote && (
        <form className="admin-review-form admin-review-note-form" onSubmit={onAddNote}>
          <label>
            <span>New note</span>
            <div className="admin-review-note-form__textarea-shell">
              <textarea
                className="pl-scrollbar pl-scrollbar--stable"
                maxLength={NOTE_MAX_LENGTH}
                placeholder="Add a private admin note..."
                spellCheck="false"
                value={noteBody}
                onChange={onNoteChange}
              />
            </div>
            <small>{noteBody.length}/{NOTE_MAX_LENGTH}</small>
          </label>
          {isAtNoteLimit && (
            <p className="admin-review-note-limit">
              This case has reached the {NOTE_CASE_LIMIT}-note limit.
            </p>
          )}
          <button
            className="admin-review-button admin-review-button--primary"
            disabled={isSubmitting || !noteBody.trim() || isAtNoteLimit}
            type="submit"
          >
            <PenLine />
            Add note
          </button>
        </form>
      )}
    </section>
  )
}

function AdminReviewCasePage() {
  const { reviewCaseId } = useParams()
  const { currentUser } = useAuth()
  const [detail, setDetail] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [noteBody, setNoteBody] = useState('')
  const [noteKey, setNoteKey] = useState(
    () => createReviewIdempotencyKey('admin-review-note', reviewCaseId),
  )
  const [closureOutcome, setClosureOutcome] = useState('enforcement_applied')
  const [closureReason, setClosureReason] = useState('')
  const [closureKey, setClosureKey] = useState(
    () => createReviewIdempotencyKey('admin-review-close', reviewCaseId),
  )
  const [formStatus, setFormStatus] = useState({ message: '', type: '' })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showNotesModal, setShowNotesModal] = useState(false)

  useEffect(() => {
    let isMounted = true

    async function loadCase() {
      if (!currentUser || !reviewCaseId) return
      setLoadState('loading')
      setPageError('')

      try {
        const response = await getAdminReviewCase({
          firebaseUser: currentUser,
          reviewCaseId,
        })
        if (!isMounted) return
        setDetail(response)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) return
        setDetail(null)
        setPageError(error.message || 'Review case could not be loaded.')
        setLoadState('error')
      }
    }

    loadCase()
    return () => {
      isMounted = false
    }
  }, [currentUser, reviewCaseId])

  function applyActionResult(result, successMessage) {
    setDetail(result.review_case)
    setFormStatus({ message: successMessage, type: 'success' })
  }

  async function handleAddNote(event) {
    event.preventDefault()
    if (
      !noteBody.trim()
      || isSubmitting
      || (detail?.notes ?? []).length >= NOTE_CASE_LIMIT
    ) {
      return
    }

    setIsSubmitting(true)
    setFormStatus({ message: '', type: '' })
    try {
      const result = await addAdminReviewCaseNote({
        body: noteBody.trim(),
        firebaseUser: currentUser,
        idempotencyKey: noteKey,
        reviewCaseId,
      })
      setDetail(result.review_case)
      setNoteBody('')
      setNoteKey(createReviewIdempotencyKey('admin-review-note', reviewCaseId))
    } catch (error) {
      setFormStatus({ message: error.message || 'Note could not be added.', type: 'error' })
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleClose(event) {
    event.preventDefault()
    if (!closureReason.trim() || isSubmitting) return

    setIsSubmitting(true)
    setFormStatus({ message: '', type: '' })
    try {
      const result = await closeAdminReviewCase({
        firebaseUser: currentUser,
        idempotencyKey: closureKey,
        outcome: closureOutcome,
        reason: closureReason.trim(),
        reviewCaseId,
      })
      applyActionResult(result, 'Review case closed.')
      setClosureReason('')
      setClosureKey(createReviewIdempotencyKey('admin-review-close', reviewCaseId))
    } catch (error) {
      setFormStatus({ message: error.message || 'Review case could not be closed.', type: 'error' })
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleNoteChange(event) {
    setNoteBody(event.target.value)
    setNoteKey(createReviewIdempotencyKey('admin-review-note', reviewCaseId))
  }

  function handleClosureReasonChange(event) {
    setClosureReason(event.target.value)
    setClosureKey(createReviewIdempotencyKey('admin-review-close', reviewCaseId))
  }

  function handleClosureOutcomeChange(event) {
    setClosureOutcome(event.target.value)
    setClosureKey(createReviewIdempotencyKey('admin-review-close', reviewCaseId))
  }

  const isClosed = detail?.case_status === 'closed'
  const findings = splitReviewFindings(detail?.findings ?? [])
  const events = detail?.events ?? []
  const targetPath = (
    detail && canOpenAdminReviewTarget(detail)
      ? getAdminReviewTargetPath(detail)
      : ''
  )

  return (
    <AdminWorkspaceLayout
      actions={(
        <Link className="admin-review-button" to="/admin/review-cases">
          <ArrowLeft />
          Back
        </Link>
      )}
      breadcrumbs={['Admin', 'Review Cases']}
      description="Inspect the internal review timeline without changing public behavior by accident."
      headerClassName="admin-review-page-header"
      icon={ClipboardList}
      title="Manage Case"
    >
      <div className="admin-review-layout">
        {pageError && (
          <FormErrorMessage className="admin-review-page-error">
            {pageError}
          </FormErrorMessage>
        )}
        {loadState === 'loading' && <p className="admin-review-empty">Loading review case.</p>}
        {loadState === 'ready' && detail && (
          <>
            <ReviewCaseOverview reviewCase={detail} targetPath={targetPath} />

            {formStatus.message && (
              <p className={`admin-review-form-status admin-review-form-status--${formStatus.type}`}>
                {formStatus.message}
              </p>
            )}

            <ReviewSection
              count={findings.current.length}
              countText={`${findings.current.length} ${
                findings.current.length === 1 ? 'finding' : 'findings'
              }`}
              icon={ClipboardList}
              title="Current Findings"
            >
              <ContentModerationFindingRows findings={findings.current} />
            </ReviewSection>

            <ReviewSection
              count={findings.previous.length}
              countText={`${findings.previous.length} ${
                findings.previous.length === 1 ? 'finding' : 'findings'
              }`}
              icon={FileClock}
              title="Previous Findings"
            >
              <ContentModerationFindingRows findings={findings.previous} />
            </ReviewSection>

            <div className="admin-review-work-grid">
              <ReviewNotesPanel
                canAddNote={!isClosed}
                className="admin-review-work-grid__notes"
                isSubmitting={isSubmitting}
                noteBody={noteBody}
                notes={detail.notes ?? []}
                onAddNote={handleAddNote}
                onNoteChange={handleNoteChange}
                onOpenHistory={() => setShowNotesModal(true)}
              />

              <ReviewSection
                className="admin-review-work-grid__close"
                icon={CheckCircle2}
                title="Close Review"
              >
                {!isClosed ? (
                  <form className="admin-review-form" onSubmit={handleClose}>
                    <label>
                      <span>Closure outcome</span>
                      <select
                        value={closureOutcome}
                        onChange={handleClosureOutcomeChange}
                      >
                        {CLOSURE_OUTCOMES.map((outcome) => (
                          <option key={outcome.value} value={outcome.value}>
                            {outcome.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      <span>Closure reason</span>
                      <textarea
                        maxLength={REASON_MAX_LENGTH}
                        placeholder="Required closure reason"
                        value={closureReason}
                        onChange={handleClosureReasonChange}
                      />
                      <small>{closureReason.length}/{REASON_MAX_LENGTH}</small>
                    </label>
                    <button
                      className="admin-review-button admin-review-button--primary"
                      disabled={isSubmitting || !closureReason.trim()}
                      type="submit"
                    >
                      <CheckCircle2 />
                      Close case
                    </button>
                  </form>
                ) : (
                  <ClosedReviewSummary reviewCase={detail} />
                )}
              </ReviewSection>

              <ReviewSection
                className="admin-review-work-grid__timeline"
                count={events.length}
                countText={`${events.length} ${events.length === 1 ? 'event' : 'events'}`}
                icon={FileClock}
                title="Timeline"
              >
                <ReviewTimelineRows
                  findings={detail.findings ?? []}
                  items={events}
                />
              </ReviewSection>
            </div>

            {showNotesModal && (
              <ReviewNotesModal
                notes={detail.notes ?? []}
                onClose={() => setShowNotesModal(false)}
              />
            )}
          </>
        )}
      </div>
    </AdminWorkspaceLayout>
  )
}

export default AdminReviewCasePage
