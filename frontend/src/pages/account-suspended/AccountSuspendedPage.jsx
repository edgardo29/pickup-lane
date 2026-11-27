import { useEffect, useState } from 'react'
import { AppPageHeader, AppPageShell } from '../../components/app/index.js'
import { useAuth } from '../../hooks/useAuth.js'
import '../../styles/account-suspended/AccountSuspendedPage.css'
import { loadSuspendedAccountNotice } from './accountSuspendedApi.js'

function AccountSuspendedPage() {
  const { currentUser } = useAuth()
  const [notice, setNotice] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let ignore = false

    loadSuspendedAccountNotice(currentUser)
      .then((result) => {
        if (!ignore) setNotice(result)
      })
      .catch((requestError) => {
        if (!ignore) {
          setError(requestError?.message || 'The suspension notice could not be loaded.')
        }
      })

    return () => {
      ignore = true
    }
  }, [currentUser])

  return (
    <AppPageShell className="account-suspended-page" mainClassName="account-suspended-shell">
      <AppPageHeader
        title="Account Suspended"
        subtitle="Your access is limited while this suspension is active."
      />

      <section className="account-suspended-card" aria-live="polite">
        {!notice && !error && <p>Loading suspension notice...</p>}
        {error && <p role="alert">{error}</p>}
        {notice && (
          <>
            <h2>{notice.notice_title}</h2>
            <p>{notice.notice_message}</p>
            <h3>What you can still do</h3>
            <ul>
              <li>View and fulfill commitments you already accepted.</li>
              <li>Manage games you already host and your existing Need a Sub arrangements.</li>
              <li>Withdraw from an existing commitment.</li>
            </ul>
            <h3>What is restricted</h3>
            <p>You cannot create a game or post, register for another game, add guests, or start new participation.</p>
          </>
        )}
      </section>
    </AppPageShell>
  )
}

export default AccountSuspendedPage
