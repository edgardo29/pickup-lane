import { Link } from 'react-router-dom'
import GameDetailsLayout from './GameDetailsLayout.jsx'
import { DetailsScaffold, DetailsState } from './GameDetailsScaffold.jsx'
import { useGameDetailsPageModel } from './useGameDetailsPageModel.js'
import '../../styles/browse-games/BrowseGamesPage.css'
import '../../styles/browse-games/GameDetailsPage.css'

function GameDetailsPage() {
  const page = useGameDetailsPageModel()

  if (page.status === 'loading') {
    return <DetailsScaffold state={<DetailsState title="Loading game" />} />
  }

  if (page.status === 'error') {
    return <DetailsScaffold state={<DetailsState title="Could not load game" message={page.error} />} />
  }

  if (!page.game || !page.viewModel || !page.layoutProps) {
    return (
      <DetailsScaffold
        state={
          <>
            <DetailsState title="Game not found" message="This game may no longer be available." />
            <Link className="details-back-link" to="/games">
              Back to games
            </Link>
          </>
        }
      />
    )
  }

  return <GameDetailsLayout {...page.layoutProps} />
}

export default GameDetailsPage
