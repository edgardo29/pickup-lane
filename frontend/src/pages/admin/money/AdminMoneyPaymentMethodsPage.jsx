import { useState } from 'react'
import {
  CreditCard,
  Search,
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
import { listAdminMoneyPaymentMethods } from '../shared/adminApi.js'

function formatExpiry(method) {
  if (!method?.exp_month || !method?.exp_year) {
    return 'No expiry'
  }

  return `${String(method.exp_month).padStart(2, '0')}/${method.exp_year}`
}

function AdminMoneyPaymentMethodsPage() {
  const { currentUser } = useAuth()
  const [draftUserId, setDraftUserId] = useState('')
  const [searchedUserId, setSearchedUserId] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [paymentMethods, setPaymentMethods] = useState([])
  const [loadState, setLoadState] = useState('idle')
  const [pageError, setPageError] = useState('')

  async function loadPaymentMethods(nextUserId, nextIncludeInactive = includeInactive) {
    if (!currentUser || !nextUserId.trim()) {
      return
    }

    setLoadState('loading')
    setPageError('')

    try {
      const nextPaymentMethods = await listAdminMoneyPaymentMethods({
        firebaseUser: currentUser,
        includeInactive: nextIncludeInactive,
        userId: nextUserId.trim(),
      })
      setPaymentMethods(nextPaymentMethods)
      setSearchedUserId(nextUserId.trim())
      setLoadState('ready')
    } catch (error) {
      setPaymentMethods([])
      setPageError(error.message || 'Saved cards could not be loaded.')
      setLoadState('error')
    }
  }

  function handleSearch(event) {
    event.preventDefault()
    loadPaymentMethods(draftUserId)
  }

  function handleIncludeInactiveChange(event) {
    const nextIncludeInactive = event.target.checked
    setIncludeInactive(nextIncludeInactive)

    if (searchedUserId) {
      loadPaymentMethods(searchedUserId, nextIncludeInactive)
    }
  }

  return (
    <AppPageShell className="admin-page" mainClassName="admin-shell">
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'Money', 'Saved Cards']}
        description="Inspect safe saved-card metadata for a selected user."
        icon={CreditCard}
        title="Saved Cards"
      >
        <div className="admin-money-layout">
          <form className="admin-money-filters admin-money-filters--cards" onSubmit={handleSearch}>
            <label>
              <span>User ID</span>
              <input
                value={draftUserId}
                onChange={(event) => setDraftUserId(event.target.value)}
              />
            </label>
            <label className="admin-money-checkbox">
              <input
                checked={includeInactive}
                type="checkbox"
                onChange={handleIncludeInactiveChange}
              />
              <span>Include inactive</span>
            </label>
            <button className="admin-money-button" type="submit">
              <Search />
              Search
            </button>
          </form>

          {pageError && (
            <div className="admin-money-alert" role="alert">
              {pageError}
            </div>
          )}

          {loadState === 'idle' && (
            <section className="admin-money-panel">
              <EmptyState>No user selected.</EmptyState>
            </section>
          )}

          {loadState === 'loading' && (
            <section className="admin-money-panel">
              <EmptyState>Loading saved cards.</EmptyState>
            </section>
          )}

          {loadState === 'ready' && (
            <section className="admin-money-panel" aria-label="Saved cards">
              <SectionHeader
                count={paymentMethods.length}
                icon={CreditCard}
                title="Saved Cards"
              />
              {paymentMethods.length === 0 ? (
                <EmptyState>No saved cards found.</EmptyState>
              ) : (
                <div className="admin-money-row-list">
                  {paymentMethods.map((method) => (
                    <div className="admin-money-row admin-money-row--four" key={method.id}>
                      <div>
                        <strong>{formatStatus(method.card_brand)} ending {method.card_last4}</strong>
                        <span>{method.is_default ? 'Default' : 'Not default'}</span>
                      </div>
                      <div>
                        <span>{formatExpiry(method)}</span>
                        <span>{formatStatus(method.method_status)}</span>
                      </div>
                      <div>
                        <span>User</span>
                        <code>{shortId(method.user_id)}</code>
                      </div>
                      <div>
                        <span>Created {formatDateTime(method.created_at)}</span>
                        <span>Updated {formatDateTime(method.updated_at)}</span>
                        <span>Detached {formatDateTime(method.detached_at)}</span>
                        <code>{shortId(method.id)}</code>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}
        </div>
      </AdminWorkspaceLayout>
    </AppPageShell>
  )
}

export default AdminMoneyPaymentMethodsPage
