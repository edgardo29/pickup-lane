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
  const subLimitMessage = isOverSpotLimit
    ? `Reduce the total to ${MAX_TOTAL_SUBS} Subs before publishing.`
    : isAtSpotLimit
      ? `Sub limit reached at ${MAX_TOTAL_SUBS}.`
      : isAtRowLimit
        ? 'All player type and position options are added.'
        : ''

  return (
    <section className="need-sub-form-section">
      <div className="need-sub-card-heading need-sub-card-heading--split">
        <div>
          <p>Sub Requirements <span>(limit {MAX_TOTAL_SUBS})</span></p>
          <small className={isOverSpotLimit ? 'need-sub-subtotal need-sub-subtotal--error' : 'need-sub-subtotal'}>
            {totalSpotsNeeded} / {MAX_TOTAL_SUBS} {totalSpotsNeeded === 1 ? 'Sub' : 'Subs'} added
          </small>
          {subLimitMessage && (
            <small className={isOverSpotLimit ? 'need-sub-subtotal need-sub-subtotal--error' : 'need-sub-subtotal'}>
              {subLimitMessage}
            </small>
          )}
        </div>
        <button disabled={!canAddSub} type="button" onClick={onAddPosition}>Add Sub</button>
      </div>

      <div className="need-sub-position-list">
        {form.positions.map((position, index) => (
          <div className="need-sub-position-card" key={`${position.sort_order}-${index}`}>
            <div className="need-sub-position-card__fields">
              <NeedASubFormField label="Position">
                <select
                  value={position.position_label}
                  onChange={(event) => onUpdatePosition(index, 'position_label', event.target.value)}
                >
                  {POSITION_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </NeedASubFormField>
              <NeedASubFormField label="Player Type">
                <select
                  value={position.player_group}
                  onChange={(event) => onUpdatePosition(index, 'player_group', event.target.value)}
                >
                  {playerGroupOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </NeedASubFormField>
              <NeedASubFormField label="Spots">
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
                className="need-sub-row-remove"
                disabled={form.positions.length === 1}
                type="button"
                onClick={() => onRemovePosition(index)}
              >
                Remove
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
