import BrowseAppNav from '../components/BrowseAppNav.jsx'
import '../styles/browse-games.css'
import '../styles/player-hub.css'

function PlayerHubPage() {
  return (
    <div className="player-hub-page">
      <BrowseAppNav />

      <main className="player-hub-shell">
        <section className="player-hub-card" aria-labelledby="player-hub-title">
          <p>Coming soon</p>
          <h1 id="player-hub-title">Player Hub</h1>
          <span>Need a Sub posts and team-player tools will live here.</span>
        </section>
      </main>
    </div>
  )
}

export default PlayerHubPage
