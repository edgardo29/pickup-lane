import {
  MAX_SUB_ROWS,
  MAX_TOTAL_SUBS,
  POSITION_OPTIONS,
  getMaxPositionRows,
  getPositionGroupOptions,
} from './needASubData.js'
import { NeedASubFormField } from './NeedASubFormField.jsx'

export function NeedASubRequirementsSection({
  form,
  hideTitle = false,
  iconActions = false,
  onAddPosition,
  onRemovePosition,
  onUpdatePosition,
  totalSpotsNeeded,
}) {
  const playerGroupOptions = getPositionGroupOptions(form.gamePlayerGroup)
  const maxPositionRows = Math.min(MAX_SUB_ROWS, getMaxPositionRows(form.gamePlayerGroup))
  const isAtSpotLimit = totalSpotsNeeded >= MAX_TOTAL_SUBS
  const isOverSpotLimit = totalSpotsNeeded > MAX_TOTAL_SUBS
  const isAtRowLimit = form.positions.length >= maxPositionRows
  const canAddSub = !isAtRowLimit && !isAtSpotLimit
  const remainingSpots = Math.max(0, MAX_TOTAL_SUBS - totalSpotsNeeded)
  const requestedLabel = `${totalSpotsNeeded} of ${MAX_TOTAL_SUBS} sub ${totalSpotsNeeded === 1 ? 'spot' : 'spots'} requested`
  const remainingLabel = `${remainingSpots} remaining`
  const isRowOptionLimit = isAtRowLimit && !isAtSpotLimit
  const subLimitMessage = isOverSpotLimit
    ? `Reduce the total to ${MAX_TOTAL_SUBS} Subs before publishing.`
    : isAtSpotLimit
      ? `Sub limit reached at ${MAX_TOTAL_SUBS}.`
      : ''

  return (
    <section className="need-sub-form-section">
      <div className="need-sub-card-heading need-sub-card-heading--split">
        <div>
          {!hideTitle && <p>Sub Requirements <span>(limit {MAX_TOTAL_SUBS})</span></p>}
          <small className={isOverSpotLimit ? 'need-sub-subtotal need-sub-subtotal--error' : 'need-sub-subtotal'}>
            {requestedLabel} · {remainingLabel}
          </small>
          {subLimitMessage && (
            <small className="need-sub-subtotal need-sub-subtotal--error">
              {subLimitMessage}
            </small>
          )}
          {isRowOptionLimit && (
            <small className="need-sub-subtotal need-sub-subtotal--note">
              <span>Note:</span> All position/player type combinations have been added. Increase "Spots" on an existing row to request more subs.
            </small>
          )}
        </div>
        <button
          aria-label="Add sub requirement"
          className={iconActions ? 'need-sub-sub-add' : undefined}
          disabled={!canAddSub}
          title="Add sub requirement"
          type="button"
          onClick={onAddPosition}
        >
          {iconActions ? '+ Add Sub' : 'Add Sub'}
        </button>
      </div>

      <div className={`need-sub-position-list${iconActions ? ' need-sub-position-list--compact' : ''}`}>
        {iconActions && (
          <div className="need-sub-position-list__header" aria-hidden="true">
            <span>Position</span>
            <span>Player Type</span>
            <span>Spots</span>
            <span />
          </div>
        )}
        {form.positions.map((position, index) => (
          <div className="need-sub-position-card" key={`${position.sort_order}-${index}`}>
            <div className={`need-sub-position-card__fields${iconActions ? ' need-sub-position-card__fields--compact' : ''}`}>
              <NeedASubFormField className={iconActions ? 'need-sub-field--compact' : ''} label="Position">
                <select
                  value={position.position_label}
                  onChange={(event) => onUpdatePosition(index, 'position_label', event.target.value)}
                >
                  {POSITION_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </NeedASubFormField>
              <NeedASubFormField className={iconActions ? 'need-sub-field--compact' : ''} label="Player Type">
                <select
                  value={position.player_group}
                  onChange={(event) => onUpdatePosition(index, 'player_group', event.target.value)}
                >
                  {playerGroupOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </NeedASubFormField>
              <NeedASubFormField className={iconActions ? 'need-sub-field--compact' : ''} label="Spots">
                <select
                  value={position.spots_needed}
                  onChange={(event) => onUpdatePosition(index, 'spots_needed', event.target.value)}
                >
                  {getSpotOptions(position.spots_needed, totalSpotsNeeded).map((spotCount) => (
                    <option key={spotCount} value={spotCount}>{spotCount}</option>
                  ))}
                </select>
              </NeedASubFormField>
              <button
                aria-hidden={iconActions && form.positions.length === 1 ? 'true' : undefined}
                aria-label={`Remove sub requirement ${index + 1}`}
                className={`need-sub-row-remove${iconActions ? ' need-sub-row-remove--icon' : ''}${iconActions && form.positions.length === 1 ? ' need-sub-row-remove--placeholder' : ''}`}
                disabled={form.positions.length === 1}
                tabIndex={iconActions && form.positions.length === 1 ? -1 : undefined}
                title="Remove sub requirement"
                type="button"
                onClick={() => onRemovePosition(index)}
              >
                {iconActions ? <span aria-hidden="true" /> : 'Remove'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function getSpotOptions(currentSpots, totalSpotsNeeded) {
  const current = Math.max(1, Number(currentSpots || 1))
  const remaining = Math.max(0, MAX_TOTAL_SUBS - Number(totalSpotsNeeded || 0))
  const maxForRow = Math.min(MAX_TOTAL_SUBS, Math.max(current, current + remaining))

  return Array.from({ length: maxForRow }, (_, index) => index + 1)
}
