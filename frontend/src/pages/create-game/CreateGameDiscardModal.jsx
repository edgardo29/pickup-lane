export function DiscardModal({ onClose, onDiscard }) {
  return (
    <div className="create-game-modal-backdrop" role="presentation">
      <div className="create-game-modal" role="dialog" aria-modal="true" aria-labelledby="discard-game-title">
        <h2 id="discard-game-title">Discard game?</h2>
        <p>Your game has not been published. Any details you entered will be lost.</p>
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
