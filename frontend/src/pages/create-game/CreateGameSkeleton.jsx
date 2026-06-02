import { AppPageHeader } from '../../components/app/index.js'
import {
  SkeletonBlock,
  SkeletonCard,
  SkeletonCircle,
} from '../../components/skeleton/index.js'
import { steps } from './createGameData.js'

const fieldSkeletons = ['date', 'start', 'end', 'format', 'group', 'skill', 'environment', 'spots', 'price']

export function CreateGameSkeleton({ isEditMode = false }) {
  return (
    <>
      <p className="skeleton-status" role="status">
        Loading {isEditMode ? 'edit game' : 'create game'}
      </p>

      <AppPageHeader
        title={isEditMode ? 'Edit Game' : 'Create Game'}
        subtitle={
          isEditMode
            ? 'Update your community game details.'
            : 'Post a community game for players to join.'
        }
      />

      <ol className="create-game-steps create-game-skeleton-steps" aria-hidden="true">
        {steps.map((step) => (
          <li className="create-game-step" key={step.id}>
            <span className="create-game-step__content create-game-skeleton-step">
              <SkeletonCircle className="create-game-skeleton-step-marker" size="28px" />
              <SkeletonBlock height="0.82rem" rounded width={step.id === 4 ? '8rem' : '4.8rem'} />
            </span>
          </li>
        ))}
      </ol>

      <section className="create-game-layout create-game-skeleton-layout" aria-hidden="true">
        <SkeletonCard className="create-game-panel create-game-skeleton-panel">
          <div className="create-game-heading create-game-skeleton-heading">
            <SkeletonBlock height="1.8rem" rounded width="18rem" />
            <SkeletonBlock height="0.82rem" rounded width="20rem" />
          </div>

          <section className="create-game-section">
            <div className="create-game-grid create-game-grid--basics create-game-skeleton-field-grid">
              {fieldSkeletons.map((item) => (
                <FieldSkeleton key={item} />
              ))}
            </div>
          </section>

          <div className="create-game-actions create-game-skeleton-actions">
            <SkeletonBlock height="38px" rounded width="88px" />
            <div className="create-game-actions__right">
              <SkeletonBlock height="38px" rounded width="88px" />
              <SkeletonBlock height="38px" rounded width="148px" />
            </div>
          </div>
        </SkeletonCard>

        <SkeletonCard className="create-game-preview create-game-skeleton-preview">
          <SkeletonBlock height="0.75rem" rounded width="6.4rem" />
          <SkeletonBlock height="1.3rem" rounded width="12rem" />

          <div className="create-game-skeleton-preview-facts">
            {fieldSkeletons.slice(0, 6).map((item) => (
              <span className="create-game-skeleton-preview-row" key={item}>
                <SkeletonCircle size="19px" />
                <SkeletonBlock height="0.82rem" rounded width={item === 'end' ? '66%' : '78%'} />
              </span>
            ))}
          </div>

          <div className="create-game-skeleton-preview-notes">
            <span className="create-game-skeleton-preview-row">
              <SkeletonCircle size="19px" />
              <SkeletonBlock height="3.8rem" rounded width="100%" />
            </span>
          </div>

          <div className="create-game-preview__money">
            <SkeletonBlock height="0.82rem" rounded width="6.4rem" />
            <SkeletonBlock height="1.2rem" rounded width="4.4rem" />
          </div>
        </SkeletonCard>
      </section>
    </>
  )
}

function FieldSkeleton() {
  return (
    <div className="create-game-field create-game-skeleton-field">
      <SkeletonBlock height="0.78rem" rounded width="48%" />
      <SkeletonBlock height="38px" rounded width="100%" />
    </div>
  )
}
