import { useEffect, useState } from 'react'
import { Trophy } from 'lucide-react'
import { useAuth } from '../../../../hooks/useAuth.js'
import '../../../../styles/admin/AdminOfficialGames.css'
import AdminWorkspaceLayout from '../../shared/AdminWorkspaceLayout.jsx'
import AdminOfficialGamesList from './AdminOfficialGamesList.jsx'
import {
  listAdminOfficialGames,
} from '../shared/adminOfficialGamesApi.js'
import { officialGameStatusOptions } from '../shared/adminOfficialGameForm.js'

function AdminOfficialGamesPage() {
  const { currentUser } = useAuth()
  const [gameStatus, setGameStatus] = useState('')
  const [games, setGames] = useState([])
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')

  useEffect(() => {
    let isMounted = true

    listAdminOfficialGames({ firebaseUser: currentUser, gameStatus })
      .then((gameResponse) => {
        if (!isMounted) {
          return
        }

        setGames(gameResponse.games ?? [])
        setPageError('')
        setLoadState('ready')
      })
      .catch((error) => {
        if (!isMounted) {
          return
        }

        setPageError(error.message || 'Official games could not be loaded.')
        setLoadState('error')
      })

    return () => {
      isMounted = false
    }
  }, [currentUser, gameStatus])

  return (
    <>
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'Games', 'Official Games']}
        description="Find and manage Pickup Lane official games."
        icon={Trophy}
        title="Official Games"
      >
        <div className="admin-official-list-layout">
          <section className="admin-official-panel admin-official-panel--list" aria-label="Official games list">
            <div className="admin-official-panel__heading admin-official-panel__heading--filter">
              <h2>Game list</h2>
              <label>
                <span>Status</span>
                <select
                  value={gameStatus}
                  onChange={(event) => {
                    setLoadState('loading')
                    setPageError('')
                    setGameStatus(event.target.value)
                  }}
                >
                  {officialGameStatusOptions.map((option) => (
                    <option key={option.value || 'all'} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
            </div>

            {pageError && <p className="admin-official-alert">{pageError}</p>}
            {loadState === 'loading' ? (
              <p className="admin-official-empty">Loading official games.</p>
            ) : (
              <AdminOfficialGamesList games={games} />
            )}
          </section>
        </div>
      </AdminWorkspaceLayout>
    </>
  )
}

export default AdminOfficialGamesPage
