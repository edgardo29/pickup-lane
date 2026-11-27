export function DiscardModal({ isEditMode = false, onClose, onDiscard }) {
  return (
    <div className="create-game-modal-backdrop" role="presentation">
      <div className="create-game-modal" role="dialog" aria-modal="true" aria-labelledby="discard-game-title">
        {/* An edited game is already published; discarding drops only the changes. */}
        <h2 id="discard-game-title">{isEditMode ? 'Discard changes?' : 'Discard game?'}</h2>
        <p>
          {isEditMode
            ? 'Your game changes have not been saved.'
            : 'Your game has not been published. Any details you entered will be lost.'}
        </p>
        <div className="create-game-modal__actions">
          <button type="button" className="create-game-secondary" onClick={onClose}>
            Keep editing
          </button>
          <button type="button" className="create-game-danger" onClick={onDiscard}>
            Discard
          </button>
        </div>
      </div>
    </div>
  )
}
