import { CloseIcon, PencilIcon } from './ProfileIcons.jsx'
import { ProfileEditForm } from './ProfileEditForm.jsx'
import { dismissOnBackdropMouseDown, useDismissibleModal } from './useModalBodyLock.js'

export function ProfileEditModal({
  currentUser,
  onClose,
  onSaved,
  settings,
}) {
  useDismissibleModal(onClose)

  return (
    <div
      className="settings-modal profile-edit-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="profile-edit-modal-title"
      onMouseDown={(event) => dismissOnBackdropMouseDown(event, onClose)}
    >
      <section className="settings-modal__card settings-modal__card--neutral profile-edit-modal__card">
        <div className="profile-edit-modal__header">
          <div>
            <h2 className="settings-modal__title" id="profile-edit-modal-title">
              <span className="settings-modal__title-icon" aria-hidden="true">
                <PencilIcon />
              </span>
              <span>Edit profile</span>
            </h2>
            <p className="settings-modal__subtitle">Update the details players and hosts see.</p>
          </div>
          <button
            className="profile-edit-modal__close"
            aria-label="Close edit profile"
            onClick={onClose}
            type="button"
          >
            <CloseIcon />
          </button>
        </div>

        <ProfileEditForm
          currentUser={currentUser}
          onCancel={onClose}
          onSaved={onSaved}
          settings={settings}
        />
      </section>
    </div>
  )
}
