import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Flag,
  RefreshCw,
} from 'lucide-react'
import { AppPageShell } from '../../../components/app/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminMoneySupport.css'
import {
  EmptyState,
  SectionHeader,
} from './AdminMoneyDetailSections.jsx'
import {
  formatDateTime,
  formatStatus,
  shortId,
} from './adminMoneyFormatters.js'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { listAdminMoneySupportFlags } from '../shared/adminApi.js'

const FLAG_STATUS_OPTIONS = [
  { label: 'Open', value: 'open' },
  { label: 'Resolved', value: 'resolved' },
  { label: 'All', value: 'all' },
]

function flagTarget(flag) {
  if (flag.target_refund_id) {
    return ['Refund', flag.target_refund_id]
  }
  if (flag.target_payment_id) {
    return ['Payment', flag.target_payment_id]
  }
  if (flag.target_game_credit_id) {
    return ['Credit', flag.target_game_credit_id]
  }
  if (flag.target_booking_id) {
    return ['Booking', flag.target_booking_id]
  }
  if (flag.target_game_id) {
    return ['Game', flag.target_game_id]
  }
  return ['Target', flag.target_user_id]
}

function AdminMoneySupportFlagsPage() {
  const { currentUser } = useAuth()
  const [flagStatus, setFlagStatus] = useState('open')
  const [supportFlags, setSupportFlags] = useState([])
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadSupportFlags() {
      if (!currentUser) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const nextSupportFlags = await listAdminMoneySupportFlags({
          firebaseUser: currentUser,
          flagStatus,
        })

        if (!isMounted) {
          return
        }

        setSupportFlags(nextSupportFlags)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setSupportFlags([])
        setPageError(error.message || 'Money support flags could not be loaded.')
        setLoadState('error')
      }
    }

    loadSupportFlags()

    return () => {
      isMounted = false
    }
  }, [currentUser, flagStatus, refreshCount])

  const pageTitle = useMemo(() => {
    if (flagStatus === 'all') {
      return 'Money Follow-Up'
    }

    return `${formatStatus(flagStatus)} Money Follow-Up`
  }, [flagStatus])

  return (
    <AppPageShell className="admin-page" mainClassName="admin-shell">
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'Money', 'Money Follow-Up']}
        description="Review money-related support flags that require attention."
        icon={Flag}
        title={pageTitle}
      >
        <div className="admin-money-layout">
          <div className="admin-money-toolbar">
            <div className="admin-money-segment" role="group" aria-label="Flag status">
              {FLAG_STATUS_OPTIONS.map((option) => (
                <button
                  aria-pressed={flagStatus === option.value}
                  className={flagStatus === option.value ? 'is-active' : ''}
                  key={option.value}
                  type="button"
                  onClick={() => setFlagStatus(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
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
              <EmptyState>Loading money support flags.</EmptyState>
            </section>
          )}

          {loadState === 'ready' && (
            <section className="admin-money-panel" aria-label="Money support flags">
              <SectionHeader
                count={supportFlags.length}
                icon={Flag}
                title="Support Flags"
              />
              {supportFlags.length === 0 ? (
                <EmptyState>No money support flags found.</EmptyState>
              ) : (
                <div className="admin-money-row-list">
                  {supportFlags.map((flag) => {
                    const [targetLabel, targetId] = flagTarget(flag)

                    return (
                      <div className="admin-money-row admin-money-row--four" key={flag.id}>
                        <div>
                          <Link className="admin-money-row-link" to={`/admin/money/support-flags/${flag.id}`}>
                            {flag.title}
                          </Link>
                          <span>{formatStatus(flag.flag_type)}</span>
                        </div>
                        <div>
                          <span>{formatStatus(flag.flag_status)}</span>
                          <em>{flag.severity}</em>
                        </div>
                        <div>
                          <span>{targetLabel}</span>
                          <code>{targetId ? shortId(targetId) : 'None'}</code>
                        </div>
                        <div>
                          <span>{formatStatus(flag.source)}</span>
                          <span>{formatDateTime(flag.updated_at)}</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </section>
          )}
        </div>
      </AdminWorkspaceLayout>
    </AppPageShell>
  )
}

export default AdminMoneySupportFlagsPage
