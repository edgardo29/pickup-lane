import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  CheckCircle2,
  Hash,
  RefreshCw,
} from 'lucide-react'
import { AppPageShell } from '../../../components/app/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminMoneySupport.css'
import {
  AuditSection,
  ContextSection,
  CreditsSection,
  EmptyState,
  PaymentsSection,
  RefundsSection,
  SectionHeader,
  SupportFlagSummary,
} from './AdminMoneyDetailSections.jsx'
import {
  formatDateTime,
  formatStatus,
} from './adminMoneyFormatters.js'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import {
  getAdminMoneySupportFlag,
  resolveAdminMoneySupportFlag,
} from '../shared/adminApi.js'

const RESOLUTION_OUTCOME_OPTIONS = [
  { label: 'Handled Externally', value: 'handled_externally' },
  { label: 'Retried Successfully', value: 'retried_successfully' },
  { label: 'No Action Needed', value: 'no_action_needed' },
  { label: 'Duplicate', value: 'duplicate' },
  { label: 'Invalid Flag', value: 'invalid_flag' },
]

function AdminMoneySupportFlagPage() {
  const { supportFlagId } = useParams()
  const { currentUser } = useAuth()
  const [detail, setDetail] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)
  const [resolveForm, setResolveForm] = useState({
    outcome: 'handled_externally',
    reason: '',
    supportFlagId: '',
  })
  const [resolveStatus, setResolveStatus] = useState({
    error: '',
    message: '',
    state: 'idle',
    supportFlagId: '',
  })

  useEffect(() => {
    let isMounted = true

    async function loadSupportFlag() {
      if (!currentUser || !supportFlagId) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const nextDetail = await getAdminMoneySupportFlag({
          firebaseUser: currentUser,
          supportFlagId,
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
        setPageError(error.message || 'Money support flag could not be loaded.')
        setLoadState('error')
      }
    }

    loadSupportFlag()

    return () => {
      isMounted = false
    }
  }, [currentUser, supportFlagId, refreshCount])

  const pageTitle = useMemo(() => (
    detail?.support_flag
      ? `${formatStatus(detail.support_flag.flag_status)} ${detail.support_flag.title}`
      : 'Support Flag'
  ), [detail])
  const activeResolveForm = resolveForm.supportFlagId === supportFlagId
    ? resolveForm
    : {
      outcome: 'handled_externally',
      reason: '',
    }
  const activeResolveStatus = resolveStatus.supportFlagId === supportFlagId
    ? resolveStatus
    : {
      error: '',
      message: '',
      state: 'idle',
    }
  const canResolve = detail?.support_flag?.flag_status === 'open'
  const resolveSubmitting = activeResolveStatus.state === 'submitting'

  async function handleResolveSupportFlag(event) {
    event.preventDefault()

    const reason = activeResolveForm.reason.trim()
    if (!canResolve) {
      setResolveStatus({
        error: 'This support flag is already resolved.',
        message: '',
        state: 'idle',
        supportFlagId,
      })
      return
    }
    if (reason.length < 3) {
      setResolveStatus({
        error: 'Reason is required.',
        message: '',
        state: 'idle',
        supportFlagId,
      })
      return
    }

    setResolveStatus({
      error: '',
      message: '',
      state: 'submitting',
      supportFlagId,
    })

    try {
      const nextDetail = await resolveAdminMoneySupportFlag({
        firebaseUser: currentUser,
        supportFlagId,
        outcome: activeResolveForm.outcome,
        reason,
      })

      setDetail(nextDetail)
      setResolveForm({
        outcome: 'handled_externally',
        reason: '',
        supportFlagId,
      })
      setResolveStatus({
        error: '',
        message: 'Support flag resolved.',
        state: 'idle',
        supportFlagId,
      })
    } catch (error) {
      setResolveStatus({
        error: error.message || 'Support flag could not be resolved.',
        message: '',
        state: 'idle',
        supportFlagId,
      })
    }
  }

  return (
    <AppPageShell className="admin-page" mainClassName="admin-shell">
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'Money', 'Money Follow-Up']}
        description="Review this support flag and its related money records."
        icon={CheckCircle2}
        title={pageTitle}
      >
        <div className="admin-money-layout">
          <div className="admin-money-toolbar">
            <Link className="admin-money-button" to="/admin/money/support-flags">
              <ArrowLeft />
              Money flags
            </Link>
            <button
              className="admin-money-button"
              type="button"
              onClick={() => setRefreshCount((count) => count + 1)}
            >
              <RefreshCw />
              Refresh
            </button>
          </div>

          {pageError && (
            <div className="admin-money-alert" role="alert">
              {pageError}
            </div>
          )}

          {loadState === 'loading' && (
            <section className="admin-money-panel">
              <EmptyState>Loading money support flag.</EmptyState>
            </section>
          )}

          {loadState === 'ready' && detail && (
            <>
              <SupportFlagSummary supportFlag={detail.support_flag} />
              <section className="admin-money-panel" aria-label="Resolve support flag">
                <SectionHeader icon={CheckCircle2} title="Resolve Flag" />
                {canResolve ? (
                  <form className="admin-money-action-form" onSubmit={handleResolveSupportFlag}>
                    <label>
                      <span>Outcome</span>
                      <select
                        disabled={resolveSubmitting}
                        onChange={(event) => {
                          setResolveForm({
                            ...activeResolveForm,
                            outcome: event.target.value,
                            supportFlagId,
                          })
                        }}
                        value={activeResolveForm.outcome}
                      >
                        {RESOLUTION_OUTCOME_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      <span>Reason</span>
                      <textarea
                        disabled={resolveSubmitting}
                        maxLength={1000}
                        onChange={(event) => {
                          setResolveForm({
                            ...activeResolveForm,
                            reason: event.target.value,
                            supportFlagId,
                          })
                        }}
                        rows={3}
                        value={activeResolveForm.reason}
                      />
                    </label>
                    <div className="admin-money-action-bar">
                      <div className="admin-money-action-status">
                        {activeResolveStatus.error && (
                          <p className="admin-money-form-error" role="alert">
                            {activeResolveStatus.error}
                          </p>
                        )}
                        {activeResolveStatus.message && (
                          <p className="admin-money-form-success" role="status">
                            {activeResolveStatus.message}
                          </p>
                        )}
                      </div>
                      <button
                        className="admin-money-button admin-money-button--primary"
                        disabled={resolveSubmitting}
                        type="submit"
                      >
                        <CheckCircle2 />
                        {resolveSubmitting ? 'Resolving' : 'Resolve Flag'}
                      </button>
                    </div>
                  </form>
                ) : (
                  <p className="admin-money-note">
                    {detail.support_flag.resolution_outcome
                      ? `${formatStatus(detail.support_flag.resolution_outcome)} on ${formatDateTime(detail.support_flag.resolved_at)}`
                      : 'This support flag is resolved.'}
                  </p>
                )}
              </section>
              <PaymentsSection payments={detail.payments ?? []} />
              <RefundsSection refunds={detail.refunds ?? []} />
              <ContextSection booking={detail.booking} game={detail.game} />
              <CreditsSection
                creditGrants={detail.credit_grants ?? []}
                creditUsages={detail.credit_usages ?? []}
              />
              <AuditSection auditActions={detail.audit_actions ?? []} />
              <section className="admin-money-panel" aria-label="Support boundary">
                <SectionHeader icon={Hash} title="Support Boundary" />
                <p className="admin-money-note">
                  Resolving a flag records staff follow-up only. Payment, refund,
                  booking, and credit state remain whatever the backend records above.
                </p>
              </section>
            </>
          )}
        </div>
      </AdminWorkspaceLayout>
    </AppPageShell>
  )
}

export default AdminMoneySupportFlagPage
