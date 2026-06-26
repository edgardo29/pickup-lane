import {
  SkeletonBlock,
  SkeletonCard,
  SkeletonCircle,
} from '../../components/skeleton/index.js'

const postCards = ['one', 'two', 'three', 'four', 'five']
const postCardFacts = ['venue', 'location', 'time', 'spec']
const detailFacts = ['date', 'time', 'location']
const needs = ['field', 'keeper', 'open']
const postNeedGroups = [
  { key: 'field', labelWidth: '5.9rem', playersWidth: '7.2rem' },
  { key: 'goalkeeper', labelWidth: '6.3rem', playersWidth: '7.2rem' },
]
const requestRows = ['pending', 'confirmed', 'waitlist']

export function NeedASubPostListSkeleton() {
  return (
    <>
      <p className="skeleton-status" role="status">
        Loading Need a Sub posts
      </p>
      <div className="need-sub-results" aria-hidden="true">
        <section className="need-sub-time-section">
          <SkeletonCard className="need-sub-time-section__header need-sub-skeleton-time-header">
            <h2>
              <SkeletonCircle size="28px" />
              <SkeletonBlock height="1.35rem" rounded width="4.2rem" />
            </h2>
            <SkeletonBlock height="34px" rounded width="5.6rem" />
          </SkeletonCard>

          <div className="need-sub-post-grid need-sub-skeleton-grid">
            {postCards.map((card) => (
              <SkeletonCard className="need-sub-post need-sub-skeleton-post" key={card}>
                <div className="need-sub-post__top">
                  <div className="need-sub-post__title-row">
                    <SkeletonBlock height="1.1rem" rounded width="7.6rem" />
                  </div>
                </div>

                <div className="need-sub-post__facts need-sub-skeleton-card-facts">
                  {postCardFacts.map((fact) => (
                    <span key={fact}>
                      <SkeletonCircle size="16px" />
                      <SkeletonBlock height="0.76rem" rounded width={fact === 'location' ? '62%' : '46%'} />
                    </span>
                  ))}
                </div>

                <div className="need-sub-post__needs">
                  <SkeletonBlock height="0.62rem" rounded width="5.4rem" />
                  {postNeedGroups.map((group) => (
                    <div className="need-sub-post__needs-group" key={group.key}>
                      <div className="need-sub-post__need-summary">
                        <SkeletonCircle size="15px" />
                        <SkeletonBlock height="0.62rem" rounded width={group.labelWidth} />
                        <SkeletonBlock height="0.72rem" rounded width="3.2rem" />
                      </div>
                      <SkeletonBlock height="0.72rem" rounded width={group.playersWidth} />
                    </div>
                  ))}
                </div>

                <div className="need-sub-post__footer">
                  <span>
                    <SkeletonCircle size="16px" />
                    <SkeletonBlock height="0.76rem" rounded width="4.6rem" />
                  </span>
                  <SkeletonCircle size="24px" />
                </div>
              </SkeletonCard>
            ))}
          </div>
        </section>
      </div>
    </>
  )
}

export function NeedASubDetailSkeleton() {
  return (
    <>
      <p className="skeleton-status" role="status">
        Loading post
      </p>
      <div className="need-sub-detail-page need-sub-detail-page--request need-sub-skeleton-detail" aria-hidden="true">
        <SkeletonCard className="need-sub-detail-hero need-sub-skeleton-detail-hero">
          <div className="need-sub-detail-hero__header">
            <div className="need-sub-detail-hero__copy">
              <div className="need-sub-detail-hero__title-row">
                <SkeletonBlock height="2.1rem" rounded width="13rem" />
              </div>
              <SkeletonBlock height="0.86rem" rounded width="13.5rem" />
            </div>
            <SkeletonBlock height="36px" rounded width="126px" />
          </div>

          <div className="need-sub-detail-game-setup">
            <span className="need-sub-detail-game-setup__label">
              <SkeletonCircle size="16px" />
              <SkeletonBlock height="0.7rem" rounded width="6.2rem" />
            </span>
            <div className="need-sub-detail-game-setup__facts">
              {['group', 'format', 'skill', 'environment'].map((fact) => (
                <span className="need-sub-detail-game-setup__fact" key={fact}>
                  <SkeletonCircle size="18px" />
                  <div>
                    <SkeletonBlock height="0.62rem" rounded width="4.4rem" />
                    <SkeletonBlock height="0.82rem" rounded width={fact === 'environment' ? '5.6rem' : '4.8rem'} />
                  </div>
                </span>
              ))}
            </div>
          </div>
        </SkeletonCard>

        <SkeletonCard className="need-sub-detail-section need-sub-post-details-card">
          <div className="need-sub-detail-section-heading need-sub-detail-section-heading--solo">
            <SkeletonCircle size="18px" />
            <SkeletonBlock height="0.72rem" rounded width="7.2rem" />
          </div>

          <div className="need-sub-post-details-grid">
            {[
              { key: 'when', className: 'need-sub-post-details-group--when', lines: ['5.4rem', '7.2rem'] },
              { key: 'where', className: 'need-sub-post-details-group--where', lines: ['6rem', '12rem', '5rem'] },
              { key: 'notes', className: 'need-sub-post-details-group--notes', lines: ['88%', '78%', '64%'] },
              { key: 'payment', className: 'need-sub-post-details-group--payment', lines: ['4rem', '7.6rem'] },
            ].map((group) => (
              <div className={`need-sub-post-details-group ${group.className}`} key={group.key}>
                <div className="need-sub-post-details-group__header">
                  <SkeletonCircle size="17px" />
                  <SkeletonBlock height="0.7rem" rounded width="5.4rem" />
                </div>
                <div className="need-sub-post-details-group__body">
                  {group.lines.map((width) => (
                    <SkeletonBlock height="0.9rem" rounded width={width} key={`${group.key}:${width}`} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </SkeletonCard>

        <div className="need-sub-detail-action-row need-sub-detail-action-row--request">
          <aside className="need-sub-detail-action-panel">
            <SkeletonCard className="need-sub-manage-card need-sub-detail-card need-sub-detail-card--request need-sub-skeleton-side-card">
              <div className="need-sub-action-card-header">
                <span className="need-sub-action-card-heading">
                  <SkeletonCircle size="18px" />
                  <SkeletonBlock height="0.72rem" rounded width="7.6rem" />
                </span>
              </div>
              <div className="need-sub-detail-choice-group">
                <SkeletonBlock height="0.62rem" rounded width="5.8rem" />
                <SkeletonBlock height="1.05rem" rounded width="9.6rem" />
                <SkeletonBlock height="0.62rem" rounded width="5.8rem" />
                <SkeletonBlock height="40px" rounded width="100%" />
              </div>
              <div className="need-sub-detail-request-box">
                <SkeletonBlock height="36px" rounded width="9rem" />
                <SkeletonBlock height="0.72rem" rounded width="80%" />
              </div>
            </SkeletonCard>
          </aside>
        </div>

        <SkeletonCard className="need-sub-detail-section need-sub-next-steps">
          <div className="need-sub-detail-section-heading need-sub-detail-section-heading--solo">
            <SkeletonCircle size="18px" />
            <SkeletonBlock height="0.72rem" rounded width="10.8rem" />
          </div>
          <div className="need-sub-next-steps__grid">
            {['request', 'review', 'notify'].map((step) => (
              <div className="need-sub-next-step" key={step}>
                <SkeletonCircle size="30px" />
                <div>
                  <SkeletonBlock height="0.92rem" rounded width="7.2rem" />
                  <SkeletonBlock height="0.74rem" rounded width="82%" />
                </div>
              </div>
            ))}
          </div>
        </SkeletonCard>
      </div>
    </>
  )
}

export function NeedASubManageSkeleton() {
  return (
    <>
      <p className="skeleton-status" role="status">
        Loading post management
      </p>
      <SkeletonCard className="need-sub-manage-hero need-sub-skeleton-manage-hero" aria-hidden="true">
        <div className="need-sub-manage-hero__summary">
          <SkeletonCircle size="64px" />
          <div className="need-sub-manage-hero__copy">
            <div className="need-sub-detail-hero__title-row">
              <SkeletonBlock height="1.9rem" rounded width="13rem" />
              <SkeletonBlock height="28px" rounded width="5rem" />
            </div>
            <SkeletonBlock height="0.86rem" rounded width="13.5rem" />
            <div className="need-sub-manage-facts need-sub-skeleton-facts">
              {detailFacts.map((fact) => (
                <span key={fact}>
                  <SkeletonCircle size="17px" />
                  <SkeletonBlock height="0.82rem" rounded width={fact === 'location' ? '12rem' : '8rem'} />
                </span>
              ))}
            </div>
          </div>
        </div>
        <div className="need-sub-manage-actions">
          <SkeletonBlock height="36px" rounded width="104px" />
          <SkeletonBlock height="36px" rounded width="104px" />
        </div>
      </SkeletonCard>

      <div className="need-sub-manage-focus-grid need-sub-skeleton-manage-grid" aria-hidden="true">
        <SkeletonCard className="need-sub-manage-card need-sub-skeleton-needs-card">
          <SkeletonBlock height="1.05rem" rounded width="8rem" />
          <div className="need-sub-need-select-list">
            {needs.map((need) => (
              <span className="need-sub-need-option need-sub-skeleton-need-option" key={need}>
                <SkeletonCircle size="34px" />
                <span className="need-sub-need-option__body">
                  <SkeletonBlock height="0.82rem" rounded width="7rem" />
                  <SkeletonBlock height="0.68rem" rounded width="5.4rem" />
                </span>
              </span>
            ))}
          </div>
        </SkeletonCard>

        <SkeletonCard className="need-sub-manage-card need-sub-player-panel need-sub-skeleton-player-card">
          <div className="need-sub-player-panel__header">
            <SkeletonBlock height="1.05rem" rounded width="9rem" />
            <SkeletonBlock height="0.82rem" rounded width="14rem" />
          </div>
          <div className="need-sub-request-tabs need-sub-skeleton-tabs">
            {requestRows.map((row) => (
              <SkeletonBlock height="36px" key={row} />
            ))}
          </div>
          <div className="need-sub-player-section">
            {requestRows.map((row) => (
              <span className="need-sub-manage-request need-sub-skeleton-request-row" key={row}>
                <SkeletonCircle size="34px" />
                <div>
                  <SkeletonBlock height="0.82rem" rounded width="8rem" />
                  <SkeletonBlock height="0.68rem" rounded width="11rem" />
                </div>
                <SkeletonBlock height="32px" rounded width="5.4rem" />
              </span>
            ))}
          </div>
        </SkeletonCard>
      </div>
    </>
  )
}
