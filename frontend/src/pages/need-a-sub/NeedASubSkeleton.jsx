import {
  SkeletonBlock,
  SkeletonCard,
  SkeletonCircle,
} from '../../components/skeleton/index.js'

const postCards = ['one', 'two', 'three', 'four']
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
      <div className="need-sub-post-grid need-sub-skeleton-grid" aria-hidden="true">
        {postCards.map((card) => (
          <SkeletonCard className="need-sub-post need-sub-skeleton-post" key={card}>
            <div className="need-sub-post__top">
              <div className="need-sub-post__title-row">
                <SkeletonBlock height="1.1rem" rounded width="7.6rem" />
                <SkeletonBlock height="24px" rounded width="4.8rem" />
              </div>
              <SkeletonBlock height="0.76rem" rounded width="58%" />
            </div>

            <div className="need-sub-post__facts need-sub-skeleton-card-facts">
              {detailFacts.map((fact) => (
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
    </>
  )
}

export function NeedASubDetailSkeleton() {
  return (
    <>
      <p className="skeleton-status" role="status">
        Loading post
      </p>
      <div className="need-sub-detail-grid need-sub-skeleton-detail" aria-hidden="true">
        <SkeletonCard className="need-sub-detail-hero need-sub-detail-card--summary need-sub-skeleton-detail-hero">
          <div className="need-sub-detail-hero__copy">
            <div className="need-sub-detail-hero__title-row">
              <SkeletonBlock height="2rem" rounded width="13rem" />
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

          <div className="need-sub-detail-divider" />

          <div className="need-sub-detail-summary-block">
            <SkeletonBlock height="0.72rem" rounded width="6rem" />
            <div className="need-sub-detail-summary need-sub-skeleton-summary">
              {needs.map((need) => (
                <span className="need-sub-detail-summary-item" key={need}>
                  <SkeletonCircle size="17px" />
                  <div>
                    <SkeletonBlock height="0.62rem" rounded width="4rem" />
                    <SkeletonBlock height="0.82rem" rounded width="7rem" />
                  </div>
                </span>
              ))}
            </div>
          </div>
        </SkeletonCard>

        <SkeletonCard className="need-sub-detail-card need-sub-detail-card--request need-sub-skeleton-side-card">
          <div className="need-sub-action-card-header">
            <SkeletonBlock height="0.72rem" rounded width="6rem" />
            <SkeletonBlock height="24px" rounded width="4.6rem" />
          </div>
          <SkeletonBlock height="0.82rem" rounded width="78%" />
          <SkeletonBlock height="38px" rounded width="100%" />
          <div className="need-sub-detail-request-box">
            <SkeletonBlock height="36px" rounded width="9rem" />
            <SkeletonBlock height="0.72rem" rounded width="80%" />
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
