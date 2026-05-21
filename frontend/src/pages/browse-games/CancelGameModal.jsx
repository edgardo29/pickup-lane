export function CancelGameModal({
  gameType,
  isCancelling,
  onClose,
  onConfirm,
}) {
  const isCommunityGame = gameType === 'community'

  return (
    <div className="details-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="details-confirm-modal details-cancel-game-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="details-cancel-game-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="details-cancel-game-title">Cancel game?</h2>
        <p>
          {isCommunityGame
            ? 'This will cancel the game for everyone and notify confirmed and waitlisted players.'
            : 'This will cancel the official game, notify players, and mark app payments for refund.'}
        </p>
        <div className="details-confirm-modal__actions">
          <button type="button" disabled={isCancelling} onClick={onClose}>
            Keep Game
          </button>
          <button className="danger" type="button" disabled={isCancelling} onClick={onConfirm}>
            {isCancelling ? 'Cancelling...' : 'Cancel Game'}
          </button>
        </div>
      </section>
    </div>
  )
}
