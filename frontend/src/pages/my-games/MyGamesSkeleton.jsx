import { AppCardGrid } from '../../components/app/index.js'
import {
  SkeletonBlock,
  SkeletonCard,
  SkeletonCircle,
} from '../../components/skeleton/index.js'

const skeletonCards = ['one', 'two', 'three', 'four', 'five', 'six']

export function MyGamesSkeleton() {
  return (
    <>
      <p className="skeleton-status" role="status">
        Loading your games
      </p>

      <div className="browse-results my-games-timeline my-games-skeleton" aria-hidden="true">
        <section className="my-games-agenda-day">
          <SkeletonCard className="time-section__header my-games-agenda-day__header my-games-skeleton-day-header">
            <span className="my-games-skeleton-day-copy">
              <SkeletonCircle size="26px" />
              <SkeletonBlock height="1.25rem" rounded width="8.6rem" />
            </span>
          </SkeletonCard>

          <AppCardGrid className="my-games-agenda-grid">
            {skeletonCards.map((card) => (
              <SkeletonCard className="game-card browse-skeleton-card my-games-skeleton-card" key={card}>
                <SkeletonBlock className="browse-skeleton-card-media my-games-skeleton-card-media" />

                <div className="game-card__body my-games-skeleton-card-body">
                  <div className="my-games-skeleton-card-heading">
                    <SkeletonBlock height="0.95rem" rounded width="56%" />
                    <SkeletonBlock height="22px" rounded width="4.8rem" />
                  </div>
                  <SkeletonBlock height="0.78rem" rounded width="42%" />
                  <SkeletonBlock height="0.78rem" rounded width="64%" />
                  <SkeletonBlock height="0.78rem" rounded width="54%" />
                </div>

                <div className="game-card__footer browse-skeleton-card-footer">
                  <SkeletonBlock height="0.82rem" rounded width="4.8rem" />
                  <SkeletonBlock height="0.82rem" rounded width="2.2rem" />
                </div>
              </SkeletonCard>
            ))}
          </AppCardGrid>
        </section>
      </div>
    </>
  )
}
