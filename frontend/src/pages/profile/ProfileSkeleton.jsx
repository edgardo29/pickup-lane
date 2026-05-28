import { AppPageHeader } from '../../components/app/index.js'
import {
  SkeletonBlock,
  SkeletonCircle,
} from '../../components/skeleton/index.js'

const statSkeletons = ['games', 'hosted', 'shows', 'cancels']
const settingsSkeletons = ['notifications', 'payment', 'support', 'terms', 'privacy', 'logout']

function ProfileStatSkeleton({ item }) {
  return (
    <article className="profile-stat-card profile-skeleton-stat-card" aria-hidden="true">
      <SkeletonCircle className="profile-stat-card__icon profile-skeleton-stat-icon" />
      <div className="profile-skeleton-stat-copy">
        <SkeletonBlock height="0.76rem" rounded width={item === 'hosted' ? '8.6rem' : '6.7rem'} />
        <SkeletonBlock height="0.62rem" rounded width={item === 'games' || item === 'hosted' ? '3.2rem' : '4.6rem'} />
      </div>
      <SkeletonBlock className="profile-skeleton-stat-value" height="1.5rem" rounded width="1.25rem" />
    </article>
  )
}

function ProfileSettingsRowSkeleton({ index }) {
  return (
    <article className="settings-row profile-skeleton-settings-row" aria-hidden="true">
      <SkeletonCircle className="settings-row__icon profile-skeleton-row-icon" />
      <span>
        <SkeletonBlock height="0.82rem" rounded width={index === 2 ? '7.3rem' : '6.4rem'} />
        <SkeletonBlock height="0.64rem" rounded width={index % 2 === 0 ? '10.2rem' : '8.6rem'} />
      </span>
      <SkeletonBlock height="1rem" rounded width="1rem" />
    </article>
  )
}

export function ProfileSkeleton() {
  return (
    <>
      <AppPageHeader title="Profile" subtitle="Manage your profile, preferences, and account." />
      <p className="skeleton-status" role="status">
        Loading profile
      </p>
      <div className="profile-hub profile-skeleton" aria-hidden="true">
        <section className="profile-overview-card profile-skeleton-overview">
          <section className="profile-hero-card profile-skeleton-hero">
            <SkeletonCircle className="profile-skeleton-avatar" />

            <div className="profile-hero-card__body profile-skeleton-hero-body">
              <div className="profile-hero-card__top">
                <SkeletonBlock className="profile-skeleton-name" height="2.3rem" rounded width="19rem" />
              </div>

              <div className="profile-meta profile-skeleton-meta">
                <SkeletonBlock height="1rem" rounded width="8rem" />
                <SkeletonBlock height="1rem" rounded width="13rem" />
              </div>

              <div className="profile-hero-actions profile-skeleton-actions">
                <SkeletonBlock height="38px" rounded width="148px" />
                <SkeletonBlock height="38px" rounded width="148px" />
              </div>
            </div>
          </section>

          <section className="profile-stat-grid profile-skeleton-stat-grid" aria-label="Loading player stats">
            {statSkeletons.map((item) => (
              <ProfileStatSkeleton item={item} key={item} />
            ))}
          </section>
        </section>

        <section
          className="profile-settings-section profile-settings-section--manage profile-skeleton-manage"
          aria-label="Loading account settings"
        >
          <div className="profile-manage-heading">
            <SkeletonCircle className="profile-manage-heading__icon profile-skeleton-manage-icon" />
            <div className="profile-skeleton-manage-copy">
              <SkeletonBlock height="1rem" rounded width="6rem" />
              <SkeletonBlock height="0.72rem" rounded width="17rem" />
            </div>
          </div>
          <div className="profile-settings-grid">
            {settingsSkeletons.map((item, index) => (
              <ProfileSettingsRowSkeleton index={index} key={item} />
            ))}
          </div>
        </section>

        <section className="profile-danger-section profile-skeleton-danger" aria-label="Loading account actions">
          <ProfileSettingsRowSkeleton index={6} />
        </section>
      </div>
    </>
  )
}
