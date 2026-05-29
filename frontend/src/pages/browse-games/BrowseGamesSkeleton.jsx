import {
  SkeletonBlock,
  SkeletonCard,
  SkeletonCircle,
} from '../../components/skeleton/index.js'

const skeletonDates = ['fri', 'sat', 'sun', 'mon', 'tue', 'wed', 'thu']
const skeletonCards = ['one', 'two', 'three', 'four']

export function BrowseGamesSkeleton() {
  return (
    <>
      <p className="skeleton-status" role="status">
        Loading games
      </p>

      <header className="browse-skeleton-header" aria-hidden="true">
        <div className="browse-skeleton-header__copy">
          <SkeletonBlock className="browse-skeleton-title" height="2.7rem" rounded width="22rem" />
          <SkeletonBlock height="1rem" rounded width="18rem" />
        </div>
      </header>

      <section className="browse-panel browse-skeleton-panel" aria-hidden="true">
        <div className="browse-date-strip-shell browse-skeleton-date-strip-shell">
          <SkeletonBlock className="browse-skeleton-date-arrow" />

          <div className="browse-date-strip browse-skeleton-date-strip">
            {skeletonDates.map((date) => (
              <SkeletonCard className="browse-date browse-skeleton-date" key={date}>
                <SkeletonBlock height="0.72rem" rounded width="2.2rem" />
                <SkeletonBlock height="0.78rem" rounded width="2rem" />
                <SkeletonBlock height="1.34rem" rounded width="1.8rem" />
              </SkeletonCard>
            ))}
          </div>

          <SkeletonBlock className="browse-skeleton-date-arrow" />
        </div>

        <div className="browse-results">
          <section className="time-section browse-skeleton-time-section">
            <SkeletonCard className="time-section__header browse-skeleton-time-header">
              <span className="browse-skeleton-time-copy">
                <SkeletonCircle size="28px" />
                <SkeletonBlock height="1.5rem" rounded width="5.2rem" />
              </span>
              <SkeletonBlock height="34px" rounded width="5.4rem" />
            </SkeletonCard>

            <div className="time-section__grid">
              {skeletonCards.map((card) => (
                <SkeletonCard className="game-card browse-skeleton-card" key={card}>
                  <SkeletonBlock className="browse-skeleton-card-media" height="118px" />
                  <div className="game-card__body browse-skeleton-card-body">
                    <SkeletonBlock height="0.95rem" rounded width="58%" />
                    <SkeletonBlock height="0.78rem" rounded width="44%" />
                    <SkeletonBlock height="0.78rem" rounded width="62%" />
                    <SkeletonBlock height="0.78rem" rounded width="54%" />
                  </div>
                  <div className="game-card__footer browse-skeleton-card-footer">
                    <SkeletonBlock height="0.82rem" rounded width="4.8rem" />
                    <SkeletonBlock height="0.82rem" rounded width="2.2rem" />
                  </div>
                </SkeletonCard>
              ))}
            </div>
          </section>
        </div>
      </section>
    </>
  )
}
