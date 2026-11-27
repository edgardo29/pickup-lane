import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AppPageHeader, AppPageShell } from '../../components/app/index.js'
import { useAuth } from '../../hooks/useAuth.js'
import '../../styles/account-suspended/AccountSuspendedPage.css'
import { loadSuspendedAccountNotice } from './accountSuspendedApi.js'

function AccountSuspendedPage() {
  const { currentUser } = useAuth()
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState(null)
  const uid = currentUser?.uid

  useEffect(() => {
    if (!currentUser) return undefined
    let ignore = false
    loadSuspendedAccountNotice(currentUser).then((notice) => {
      if (!ignore) setResult({ uid, attempt, notice })
    }).catch((error) => {
      if (!ignore) setResult({ uid, attempt, missing: error?.status === 404, error: true })
    })
    return () => { ignore = true }
  }, [attempt, currentUser, uid])

  const loaded = result?.uid === uid && result.attempt === attempt ? result : null
  const notice = loaded?.notice

  return (
    <AppPageShell className="account-suspended-page" mainClassName="account-suspended-shell">
      <AppPageHeader
        title="Account Suspended"
        subtitle="Your access is limited while this suspension is active."
      />

      <section className="account-suspended-card">
        <h2>What you can still do</h2>
        <ul>
          <li>View and fulfill commitments you already accepted.</li>
          <li>Manage games you already host and your existing Need a Sub arrangements.</li>
          <li>Withdraw from an existing commitment.</li>
          <li>Chat and manage host guests for games you already host.</li>
        </ul>
        <Link to="/my-games">View my games and Sub Post commitments</Link>
        <h2>What is restricted</h2>
        <p>You cannot create a game or post, register for another game, add guests, or start new participation.</p>
        <p>Staff actions are unavailable.</p>
        <section aria-labelledby="suspension-notice-title">
          <h2 id="suspension-notice-title">Suspension notice</h2>
          {!loaded && <p role="status">Loading your suspension notice...</p>}
          {loaded?.missing ? (
            <p>No suspension notice is available. Contact support for help.</p>
          ) : loaded?.error ? (
            <>
              <p role="alert">Could not load your suspension notice. Try again.</p>
              <button type="button" onClick={() => setAttempt((value) => value + 1)}>
                Try again
              </button>
            </>
          ) : notice && (
            <><h3>{notice.notice_title}</h3><p>{notice.notice_message}</p></>
          )}
        </section>
      </section>
    </AppPageShell>
  )
}

export default AccountSuspendedPage
