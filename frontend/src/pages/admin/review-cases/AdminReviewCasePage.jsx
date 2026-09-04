import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  CheckCircle2,
  ClipboardList,
  FileClock,
  Link2,
  MessageSquareText,
  MessagesSquare,
  PenLine,
  RefreshCcw,
  UserRound,
  X,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminReviewCases.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import {
  addAdminReviewCaseNote,
  assignAdminReviewCase,
  closeAdminReviewCase,
  getAdminReviewCase,
  listAdminReviewCases,
  listAdminUsers,
  mergeAdminReviewCase,
  reopenAdminReviewCase,
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
import {
  areReviewLifecycleActionsBlocked,
  canMergeReviewCaseSource,
  collectCursorPages,
  describeReviewCaseAssignment,
  getReviewCaseConflictSnapshot,
  getVisibleResolutionHistory,
  isCompatibleMergeDestination,
  reviewCaseConflictSnapshotMatchesCase,
  reviewCaseStateScopeKey,
  sortReviewCaseEvents,
} from './adminReviewLifecycle.js'
import { AdminResolutionReferenceList } from './AdminResolutionReferenceList.js'

const NOTE_MAX_LENGTH = 1000
const NOTE_CASE_LIMIT = 100
const REASON_MAX_LENGTH = 1000
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
          label="Category"
          value={formatAdminReviewStatus(reviewCase.case_category)}
        />
        <ReviewField
          label="Version"
          value={reviewCase.case_version}
        />
        <ReviewField
          label="Assignment"
          value={describeReviewCaseAssignment(reviewCase)}
        />
        <ReviewField
          label="Content status"
          value={targetStatus || 'Unknown'}
        />
        <ReviewField
          label="Updated"
          value={formatAdminReviewDateTime(reviewCase.updated_at)}
        />
        {reviewCase.merged_into_case_id && (
          <ReviewField
            label="Merged into"
            value={shortAdminReviewId(reviewCase.merged_into_case_id)}
          />
        )}
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

function ResolutionHistoryRows({ reviewCase }) {
  const history = getVisibleResolutionHistory(reviewCase)
  if (!history.length) {
    return <p className="admin-review-empty">No prior resolutions.</p>
  }

  return (
    <div className="admin-review-resolution-history">
      {history.map((resolution) => (
        <article key={resolution.closure_event_id}>
          <div className="admin-review-resolution-history__heading">
            <strong>{formatAdminReviewStatus(resolution.outcome)}</strong>
            <time dateTime={resolution.closed_at}>
              {formatAdminReviewDateTime(resolution.closed_at)}
            </time>
          </div>
          <p>{resolution.reason}</p>
          <div className="admin-review-resolution-history__facts">
            <span>{formatAdminReviewStatus(resolution.mode)}</span>
            <span>
              {resolution.mode === 'automatic'
                ? `${resolution.automation_rule_id} v${resolution.automation_rule_version}`
                : `Admin ${shortAdminReviewId(resolution.actor_user_id)}`}
            </span>
            <span>{resolution.references.length} linked records</span>
          </div>
          <AdminResolutionReferenceList references={resolution.references} />
        </article>
      ))}
    </div>
  )
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
    case 'assignment_changed':
      return 'Assignment changed'
    case 'closed':
      return 'Case closed'
    case 'reopened':
      return 'Case reopened'
    case 'merged_into':
      return 'Merged into another case'
    case 'merged_from':
      return 'Merged case linked'
    case 'signal_superseded':
      return 'Chat signal superseded'
    case 'signal_reactivated':
      return 'Chat signal reactivated'
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
  const timelineItems = sortReviewCaseEvents(items)

  return (
    <div className="admin-review-timeline">
      {timelineItems.map((item) => (
        <div className="admin-review-timeline-row" key={item.id}>
          <strong>
            <span>#{item.event_sequence}</span>
            {formatTimelineEventTitle(item, findingById)}
          </strong>
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

function ChatSignalRows({ signals }) {
  if (!signals.length) {
    return <p className="admin-review-empty">No chat signals.</p>
  }

  return (
    <div className="admin-review-list admin-review-list--compact">
      {signals.map((signal) => (
        <article className="admin-review-finding-row" key={signal.id}>
          <div className="admin-review-finding-row__summary">
            <strong>{signal.title}</strong>
            <span>{formatAdminReviewStatus(signal.priority)}</span>
          </div>
          <p className="admin-review-finding-row__updated">
            {signal.summary}
          </p>
        </article>
      ))}
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
      {note.corrects_note_id && (
        <span className="admin-review-note__correction">
          Corrects note {shortAdminReviewId(note.corrects_note_id)}
        </span>
      )}
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
  actionsBlocked,
  canAddNote,
  className = '',
  noteBody,
  correctsNoteId,
  notes,
  onAddNote,
  onNoteChange,
  onCorrectionChange,
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
                disabled={actionsBlocked}
                maxLength={NOTE_MAX_LENGTH}
                placeholder="Add a private admin note..."
                spellCheck="false"
                value={noteBody}
                onChange={onNoteChange}
              />
            </div>
            <small>{noteBody.length}/{NOTE_MAX_LENGTH}</small>
          </label>
          {notes.length > 0 && (
            <label>
              <span>Correction to</span>
              <select
                disabled={actionsBlocked}
                value={correctsNoteId}
                onChange={onCorrectionChange}
              >
                <option value="">New note</option>
                {orderedNotes.map((note) => (
                  <option key={note.id} value={note.id}>
                    Note {shortAdminReviewId(note.id)}
                  </option>
                ))}
              </select>
            </label>
          )}
          {isAtNoteLimit && (
            <p className="admin-review-note-limit">
              This case has reached the {NOTE_CASE_LIMIT}-note limit.
            </p>
          )}
          <button
            className="admin-review-button admin-review-button--primary"
            disabled={actionsBlocked || !noteBody.trim() || isAtNoteLimit}
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

function AdminReviewCasePageContent({ reviewCaseId }) {
  const { currentUser } = useAuth()
  const [detail, setDetail] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [noteBody, setNoteBody] = useState('')
  const [correctsNoteId, setCorrectsNoteId] = useState('')
  const [noteKey, setNoteKey] = useState(
    () => createReviewIdempotencyKey('admin-review-note', reviewCaseId),
  )
  const [closureOutcome, setClosureOutcome] = useState('enforcement_applied')
  const [closureReason, setClosureReason] = useState('')
  const [closureKey, setClosureKey] = useState(
    () => createReviewIdempotencyKey('admin-review-close', reviewCaseId),
  )
  const [assignmentUserId, setAssignmentUserId] = useState('')
  const [assignmentReason, setAssignmentReason] = useState('')
  const [assignmentKey, setAssignmentKey] = useState(
    () => createReviewIdempotencyKey('admin-review-assignment', reviewCaseId),
  )
  const [reopenReason, setReopenReason] = useState('')
  const [reopenKey, setReopenKey] = useState(
    () => createReviewIdempotencyKey('admin-review-reopen', reviewCaseId),
  )
  const [mergeDestinationId, setMergeDestinationId] = useState('')
  const [mergeReason, setMergeReason] = useState('')
  const [mergeKey, setMergeKey] = useState(
    () => createReviewIdempotencyKey('admin-review-merge', reviewCaseId),
  )
  const [adminChoices, setAdminChoices] = useState([])
  const [compatibleCases, setCompatibleCases] = useState([])
  const [assignmentOptionsState, setAssignmentOptionsState] = useState({
    error: '',
    loading: true,
  })
  const [mergeOptionsState, setMergeOptionsState] = useState({
    error: '',
    loading: true,
  })
  const [formStatus, setFormStatus] = useState({ message: '', type: '' })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [conflictRecoveryBlocked, setConflictRecoveryBlocked] = useState(false)
  const [showNotesModal, setShowNotesModal] = useState(false)

  const fetchReviewCase = useCallback(() => getAdminReviewCase({
    firebaseUser: currentUser,
    reviewCaseId,
  }), [currentUser, reviewCaseId])

  useEffect(() => {
    let isMounted = true

    async function loadCase() {
      if (!currentUser || !reviewCaseId) return
      setLoadState('loading')
      setPageError('')

      try {
        const response = await fetchReviewCase()
        if (!isMounted) return
        setDetail(response)
        setAssignmentUserId(response.assigned_to_user_id ?? '')
        setConflictRecoveryBlocked(false)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) return
        setDetail(null)
        setAssignmentUserId('')
        setPageError(error.message || 'Review case could not be loaded.')
        setLoadState('error')
      }
    }

    loadCase()
    return () => {
      isMounted = false
    }
  }, [currentUser, fetchReviewCase, reviewCaseId])

  useEffect(() => {
    let isMounted = true
    if (!currentUser || !detail) return () => {}

    async function loadAssignmentChoices() {
      await Promise.resolve()
      if (!isMounted) return
      setAdminChoices([])
      setAssignmentOptionsState({ error: '', loading: true })
      try {
        const users = await collectCursorPages(
          (cursor) => listAdminUsers({
            accountStatus: 'active',
            cursor,
            firebaseUser: currentUser,
            limit: 100,
            role: 'admin',
          }),
          'users',
        )
        if (!isMounted) return
        setAdminChoices(users)
        setAssignmentOptionsState({ error: '', loading: false })
      } catch {
        if (!isMounted) return
        setAdminChoices([])
        setAssignmentOptionsState({
          error: 'Assignment choices could not be loaded.',
          loading: false,
        })
      }
    }

    async function loadMergeChoices() {
      await Promise.resolve()
      if (!isMounted) return
      setCompatibleCases([])
      if (!canMergeReviewCaseSource(detail)) {
        setMergeOptionsState({ error: '', loading: false })
        return
      }
      setMergeOptionsState({ error: '', loading: true })
      try {
        const cases = await collectCursorPages(
          (cursor) => listAdminReviewCases({
            assignment: 'all',
            caseCategory: detail.case_category,
            caseStatus: 'open',
            cursor,
            firebaseUser: currentUser,
            limit: 100,
            targetType: detail.case_type,
          }),
          'cases',
        )
        if (!isMounted) return
        setCompatibleCases(
          cases.filter((candidate) => isCompatibleMergeDestination(detail, candidate)),
        )
        setMergeOptionsState({ error: '', loading: false })
      } catch {
        if (!isMounted) return
        setCompatibleCases([])
        setMergeOptionsState({
          error: 'Merge destinations could not be loaded.',
          loading: false,
        })
      }
    }

    loadAssignmentChoices()
    loadMergeChoices()

    return () => {
      isMounted = false
    }
  }, [currentUser, detail])

  async function handleMutationError(error, fallbackMessage) {
    const snapshot = getReviewCaseConflictSnapshot(error)
    if (snapshot) {
      setConflictRecoveryBlocked(true)
      if (reviewCaseConflictSnapshotMatchesCase(snapshot, reviewCaseId)) {
        setDetail((current) => ({ ...current, ...snapshot }))
        setAssignmentUserId(snapshot.assigned_to_user_id ?? '')
      }
      setFormStatus({
        message: 'This case changed. Reloading the complete current state.',
        type: 'error',
      })
      try {
        const currentDetail = await fetchReviewCase()
        setDetail(currentDetail)
        setAssignmentUserId(currentDetail.assigned_to_user_id ?? '')
        setPageError('')
        setConflictRecoveryBlocked(false)
        setFormStatus({
          message: 'This case changed. The latest state has been loaded.',
          type: 'error',
        })
        resetMutationKeys()
      } catch {
        setPageError('The latest review case could not be loaded.')
        setFormStatus({
          message: 'Lifecycle actions are blocked until the latest case reload succeeds.',
          type: 'error',
        })
      }
      return
    }
    setFormStatus({ message: error.message || fallbackMessage, type: 'error' })
  }

  function applyActionResult(result, successMessage) {
    setDetail(result.review_case)
    setAssignmentUserId(result.review_case.assigned_to_user_id ?? '')
    setFormStatus({ message: successMessage, type: 'success' })
  }

  function resetMutationKeys() {
    setNoteKey(createReviewIdempotencyKey('admin-review-note', reviewCaseId))
    setClosureKey(createReviewIdempotencyKey('admin-review-close', reviewCaseId))
    setAssignmentKey(createReviewIdempotencyKey('admin-review-assignment', reviewCaseId))
    setReopenKey(createReviewIdempotencyKey('admin-review-reopen', reviewCaseId))
    setMergeKey(createReviewIdempotencyKey('admin-review-merge', reviewCaseId))
  }

  async function retryConflictRecovery() {
    if (!conflictRecoveryBlocked || isSubmitting) return
    setIsSubmitting(true)
    try {
      const currentDetail = await fetchReviewCase()
      setDetail(currentDetail)
      setAssignmentUserId(currentDetail.assigned_to_user_id ?? '')
      setPageError('')
      setConflictRecoveryBlocked(false)
      setFormStatus({ message: 'The latest case state has been loaded.', type: 'success' })
      resetMutationKeys()
    } catch (error) {
      setPageError(error.message || 'The latest review case could not be loaded.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const actionsBlocked = areReviewLifecycleActionsBlocked({
    conflictRecoveryBlocked,
    isSubmitting,
  })

  async function handleAddNote(event) {
    event.preventDefault()
    if (
      !noteBody.trim()
      || actionsBlocked
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
        correctsNoteId: correctsNoteId || null,
        expectedCaseVersion: detail.case_version,
      })
      setDetail(result.review_case)
      setAssignmentUserId(result.review_case.assigned_to_user_id ?? '')
      setNoteBody('')
      setCorrectsNoteId('')
      setNoteKey(createReviewIdempotencyKey('admin-review-note', reviewCaseId))
    } catch (error) {
      await handleMutationError(error, 'Note could not be added.')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleClose(event) {
    event.preventDefault()
    if (!closureReason.trim() || actionsBlocked) return

    setIsSubmitting(true)
    setFormStatus({ message: '', type: '' })
    try {
      const result = await closeAdminReviewCase({
        firebaseUser: currentUser,
        idempotencyKey: closureKey,
        outcome: closureOutcome,
        reason: closureReason.trim(),
        reviewCaseId,
        expectedCaseVersion: detail.case_version,
      })
      applyActionResult(result, 'Review case closed.')
      setClosureReason('')
      setClosureKey(createReviewIdempotencyKey('admin-review-close', reviewCaseId))
    } catch (error) {
      await handleMutationError(error, 'Review case could not be closed.')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleAssignment(event) {
    event.preventDefault()
    if (!assignmentReason.trim() || actionsBlocked) return
    setIsSubmitting(true)
    setFormStatus({ message: '', type: '' })
    try {
      const result = await assignAdminReviewCase({
        assigneeUserId: assignmentUserId || null,
        expectedCaseVersion: detail.case_version,
        firebaseUser: currentUser,
        idempotencyKey: assignmentKey,
        reason: assignmentReason.trim(),
        reviewCaseId,
      })
      applyActionResult(result, assignmentUserId ? 'Assignment updated.' : 'Assignment released.')
      setAssignmentReason('')
      setAssignmentKey(createReviewIdempotencyKey('admin-review-assignment', reviewCaseId))
    } catch (error) {
      await handleMutationError(error, 'Assignment could not be changed.')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleReopen(event) {
    event.preventDefault()
    if (!reopenReason.trim() || actionsBlocked) return
    setIsSubmitting(true)
    setFormStatus({ message: '', type: '' })
    try {
      const result = await reopenAdminReviewCase({
        expectedCaseVersion: detail.case_version,
        firebaseUser: currentUser,
        idempotencyKey: reopenKey,
        reason: reopenReason.trim(),
        reviewCaseId,
      })
      applyActionResult(result, 'Review case reopened.')
      setReopenReason('')
      setReopenKey(createReviewIdempotencyKey('admin-review-reopen', reviewCaseId))
    } catch (error) {
      await handleMutationError(error, 'Review case could not be reopened.')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleMerge(event) {
    event.preventDefault()
    const destination = compatibleCases.find((item) => item.id === mergeDestinationId)
    if (!destination || !mergeReason.trim() || actionsBlocked) return
    setIsSubmitting(true)
    setFormStatus({ message: '', type: '' })
    try {
      const result = await mergeAdminReviewCase({
        destinationCaseId: destination.id,
        expectedDestinationVersion: destination.case_version,
        expectedSourceVersion: detail.case_version,
        firebaseUser: currentUser,
        idempotencyKey: mergeKey,
        reason: mergeReason.trim(),
        reviewCaseId,
      })
      setDetail(result.source_case)
      setAssignmentUserId(result.source_case.assigned_to_user_id ?? '')
      setFormStatus({ message: 'Review cases merged.', type: 'success' })
      setMergeDestinationId('')
      setMergeReason('')
      setMergeKey(createReviewIdempotencyKey('admin-review-merge', reviewCaseId))
    } catch (error) {
      await handleMutationError(error, 'Review cases could not be merged.')
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleNoteChange(event) {
    setNoteBody(event.target.value)
    setNoteKey(createReviewIdempotencyKey('admin-review-note', reviewCaseId))
  }

  function handleCorrectionChange(event) {
    setCorrectsNoteId(event.target.value)
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

  function handleAssignmentSelection(event) {
    setAssignmentUserId(event.target.value)
    setAssignmentKey(createReviewIdempotencyKey('admin-review-assignment', reviewCaseId))
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
          <div className="admin-review-page-error">
            <FormErrorMessage>{pageError}</FormErrorMessage>
            {conflictRecoveryBlocked && (
              <button
                className="admin-review-button"
                disabled={isSubmitting}
                type="button"
                onClick={retryConflictRecovery}
              >
                <RefreshCcw />
                Reload current case
              </button>
            )}
          </div>
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

            {detail.case_category === 'content_moderation' ? (
              <>
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
              </>
            ) : (
              <ReviewSection
                count={(detail.signals ?? []).length}
                icon={MessagesSquare}
                title="Chat Signals"
              >
                <ChatSignalRows signals={detail.signals ?? []} />
              </ReviewSection>
            )}

            <ReviewSection icon={UserRound} title="Case Workflow">
              <div className="admin-review-action-forms">
                {!isClosed && (
                  <form className="admin-review-form" onSubmit={handleAssignment}>
                    <label>
                      <span>Assignment</span>
                      <select
                        disabled={actionsBlocked || assignmentOptionsState.loading || Boolean(assignmentOptionsState.error)}
                        value={assignmentUserId}
                        onChange={handleAssignmentSelection}
                      >
                        <option value="">Unassigned</option>
                        {adminChoices.map((user) => (
                          <option key={user.id} value={user.id}>
                            {user.display_name || user.email || shortAdminReviewId(user.id)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      <span>Reason</span>
                      <input
                        maxLength={1000}
                        disabled={actionsBlocked}
                        value={assignmentReason}
                        onChange={(event) => {
                          setAssignmentReason(event.target.value)
                          setAssignmentKey(createReviewIdempotencyKey('admin-review-assignment', reviewCaseId))
                        }}
                      />
                    </label>
                    <button
                      className="admin-review-button"
                      disabled={actionsBlocked || assignmentOptionsState.loading || Boolean(assignmentOptionsState.error) || !assignmentReason.trim()}
                      type="submit"
                    >
                      <UserRound />
                      Update assignment
                    </button>
                  </form>
                )}

                {assignmentOptionsState.error && (
                  <p className="admin-review-form-status admin-review-form-status--error">
                    {assignmentOptionsState.error}
                  </p>
                )}

                {isClosed && !detail.merged_into_case_id && (
                  <form className="admin-review-form" onSubmit={handleReopen}>
                    <label>
                      <span>Reopen reason</span>
                      <input
                        maxLength={1000}
                        disabled={actionsBlocked}
                        value={reopenReason}
                        onChange={(event) => {
                          setReopenReason(event.target.value)
                          setReopenKey(createReviewIdempotencyKey('admin-review-reopen', reviewCaseId))
                        }}
                      />
                    </label>
                    <button
                      className="admin-review-button"
                      disabled={actionsBlocked || !reopenReason.trim()}
                      type="submit"
                    >
                      <RefreshCcw />
                      Reopen case
                    </button>
                  </form>
                )}

                {canMergeReviewCaseSource(detail) && compatibleCases.length > 0 && (
                  <form className="admin-review-form" onSubmit={handleMerge}>
                    <label>
                      <span>Merge into</span>
                      <select
                        value={mergeDestinationId}
                        disabled={actionsBlocked || mergeOptionsState.loading || Boolean(mergeOptionsState.error)}
                        onChange={(event) => {
                          setMergeDestinationId(event.target.value)
                          setMergeKey(createReviewIdempotencyKey('admin-review-merge', reviewCaseId))
                        }}
                      >
                        <option value="">Select case</option>
                        {compatibleCases.map((reviewCase) => (
                          <option key={reviewCase.id} value={reviewCase.id}>
                            {shortAdminReviewId(reviewCase.id)} · v{reviewCase.case_version}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      <span>Merge reason</span>
                      <input
                        maxLength={1000}
                        disabled={actionsBlocked}
                        value={mergeReason}
                        onChange={(event) => {
                          setMergeReason(event.target.value)
                          setMergeKey(createReviewIdempotencyKey('admin-review-merge', reviewCaseId))
                        }}
                      />
                    </label>
                    <button
                      className="admin-review-button"
                      disabled={actionsBlocked || !mergeDestinationId || !mergeReason.trim()}
                      type="submit"
                    >
                      <Link2 />
                      Merge cases
                    </button>
                  </form>
                )}
                {mergeOptionsState.error && (
                  <p className="admin-review-form-status admin-review-form-status--error">
                    {mergeOptionsState.error}
                  </p>
                )}
              </div>
              {(detail.linked_cases ?? []).length > 0 && (
                <div className="admin-review-linked-cases">
                  {detail.linked_cases.map((linkedCase) => (
                    <Link key={linkedCase.id} to={`/admin/review-cases/${linkedCase.id}`}>
                      {formatAdminReviewStatus(linkedCase.relation)} · {shortAdminReviewId(linkedCase.id)}
                    </Link>
                  ))}
                </div>
              )}
            </ReviewSection>

            <ReviewSection
              count={(detail.resolution_history ?? []).length}
              icon={FileClock}
              title="Resolution History"
            >
              <ResolutionHistoryRows reviewCase={detail} />
            </ReviewSection>

            <div className="admin-review-work-grid">
              <ReviewNotesPanel
                canAddNote={!isClosed}
                className="admin-review-work-grid__notes"
                actionsBlocked={actionsBlocked}
                noteBody={noteBody}
                correctsNoteId={correctsNoteId}
                notes={detail.notes ?? []}
                onAddNote={handleAddNote}
                onCorrectionChange={handleCorrectionChange}
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
                        disabled={actionsBlocked}
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
                        disabled={actionsBlocked}
                        maxLength={REASON_MAX_LENGTH}
                        placeholder="Required closure reason"
                        value={closureReason}
                        onChange={handleClosureReasonChange}
                      />
                      <small>{closureReason.length}/{REASON_MAX_LENGTH}</small>
                    </label>
                    <button
                      className="admin-review-button admin-review-button--primary"
                      disabled={actionsBlocked || !closureReason.trim()}
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

function AdminReviewCasePage() {
  const { reviewCaseId } = useParams()
  return (
    <AdminReviewCasePageContent
      key={reviewCaseStateScopeKey(reviewCaseId)}
      reviewCaseId={reviewCaseId}
    />
  )
}

export default AdminReviewCasePage
