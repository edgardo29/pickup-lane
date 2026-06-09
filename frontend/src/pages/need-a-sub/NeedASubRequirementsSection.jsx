import {
  MAX_SUB_ROWS,
  MAX_TOTAL_SUBS,
  POSITION_OPTIONS,
  getNextPosition,
  getPositionGroupOptions,
  positionGroupCreatesAnyConflict,
  positionLabelCreatesAnyConflict,
} from './needASubData.js'
import {
  getMinimumEditableSpots,
  hasActivePositionRequests,
} from './needASubSelectors.js'
import { NeedASubFormField } from './NeedASubFormField.jsx'

export function NeedASubRequirementsSection({
  form,
  hideTitle = false,
  iconActions = false,
  isEditMode = false,
  onAddPosition,
  onRemovePosition,
  onUpdatePosition,
  totalSpotsNeeded,
}) {
  const playerGroupOptions = getPositionGroupOptions(form.gamePlayerGroup)
  const nextPosition = getNextPosition(form.positions, form.gamePlayerGroup)
  const isAtSpotLimit = totalSpotsNeeded >= MAX_TOTAL_SUBS
  const isOverSpotLimit = totalSpotsNeeded > MAX_TOTAL_SUBS
  const isAtRowLimit = form.positions.length >= MAX_SUB_ROWS || !nextPosition
  const remainingSpots = Math.max(0, MAX_TOTAL_SUBS - totalSpotsNeeded)
  const requestedLabel = `${totalSpotsNeeded} of ${MAX_TOTAL_SUBS} sub ${totalSpotsNeeded === 1 ? 'spot' : 'spots'} requested`
  const remainingLabel = `${remainingSpots} remaining`
  const hasIncompletePlayerGroup = form.positions.some((position) => !position.player_group)
  const hasAnyPlayerRow = form.positions.some((position) => position.player_group === 'open')
  const hasLockedRows = form.positions.some((position) => isEditMode && hasActivePositionRequests(position))
  const isRowOptionLimit = (isAtRowLimit || hasIncompletePlayerGroup) && !isAtSpotLimit
  const canAddSub = !hasIncompletePlayerGroup && !isAtRowLimit && !isAtSpotLimit
  const subLimitMessage = isOverSpotLimit
    ? `Reduce the total to ${MAX_TOTAL_SUBS} Subs before publishing.`
    : isAtSpotLimit
      ? `Sub limit reached at ${MAX_TOTAL_SUBS}.`
      : ''
  const rowOptionMessage = getRowOptionMessage(hasIncompletePlayerGroup, hasAnyPlayerRow)

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
              <span>Note:</span> {rowOptionMessage}
            </small>
          )}
          {hasLockedRows && (
            <small className="need-sub-subtotal need-sub-subtotal--note">
              <span>Note:</span> Rows with active requests keep their position and player group.
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
            <span>Player Group</span>
            <span>Spots</span>
            <span />
          </div>
        )}
        {form.positions.map((position, index) => (
          <div className="need-sub-position-card" key={`${position.sort_order}-${index}`}>
            <div className={`need-sub-position-card__fields${iconActions ? ' need-sub-position-card__fields--compact' : ''}`}>
              <NeedASubFormField className={iconActions ? 'need-sub-field--compact' : ''} label="Position">
                <select
                  disabled={isPositionTypeLocked(position, isEditMode)}
                  value={position.position_label}
                  onChange={(event) => onUpdatePosition(index, 'position_label', event.target.value)}
                >
                  {POSITION_OPTIONS.map((option) => (
                    <option
                      disabled={positionLabelCreatesAnyConflict(
                        option.value,
                        form.positions,
                        index,
                        position.player_group,
                      )}
                      key={option.value}
                      value={option.value}
                    >
                      {option.label}
                    </option>
                  ))}
                </select>
              </NeedASubFormField>
              <NeedASubFormField className={iconActions ? 'need-sub-field--compact' : ''} label="Player group">
                <select
                  disabled={isPositionTypeLocked(position, isEditMode)}
                  value={position.player_group}
                  onChange={(event) => onUpdatePosition(index, 'player_group', event.target.value)}
                >
                  <option value="">Select</option>
                  {playerGroupOptions.map((option) => (
                    <option
                      disabled={positionGroupCreatesAnyConflict(
                        option.value,
                        form.positions,
                        index,
                        position.position_label,
                      )}
                      key={option.value}
                      value={option.value}
                    >
                      {option.label}
                    </option>
                  ))}
                </select>
              </NeedASubFormField>
              <NeedASubFormField className={iconActions ? 'need-sub-field--compact' : ''} label="Spots">
                <select
                  value={position.spots_needed}
                  onChange={(event) => onUpdatePosition(index, 'spots_needed', event.target.value)}
                >
                  {getSpotOptions(
                    position.spots_needed,
                    totalSpotsNeeded,
                    isEditMode ? getMinimumEditableSpots(position) : 1,
                  ).map((spotCount) => (
                    <option key={spotCount} value={spotCount}>{spotCount}</option>
                  ))}
                </select>
              </NeedASubFormField>
              <button
                aria-hidden={iconActions && form.positions.length === 1 ? 'true' : undefined}
                aria-label={`Remove sub requirement ${index + 1}`}
                className={`need-sub-row-remove${iconActions ? ' need-sub-row-remove--icon' : ''}${iconActions && form.positions.length === 1 ? ' need-sub-row-remove--placeholder' : ''}`}
                disabled={form.positions.length === 1 || isPositionTypeLocked(position, isEditMode)}
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

function getSpotOptions(currentSpots, totalSpotsNeeded, minimumSpots = 1) {
  const current = Math.max(1, Number(currentSpots || 1))
  const remaining = Math.max(0, MAX_TOTAL_SUBS - Number(totalSpotsNeeded || 0))
  const minimum = Math.max(1, Number(minimumSpots || 1))
  const maxForRow = Math.min(MAX_TOTAL_SUBS, Math.max(minimum, current, current + remaining))
  const start = Math.min(minimum, maxForRow)

  return Array.from({ length: maxForRow - start + 1 }, (_, index) => start + index)
}

function isPositionTypeLocked(position, isEditMode) {
  return Boolean(isEditMode && hasActivePositionRequests(position))
}

function getRowOptionMessage(hasIncompletePlayerGroup, hasAnyPlayerRow) {
  if (hasIncompletePlayerGroup) {
    return 'Choose a player group on an existing row before adding more rows for that position.'
  }

  if (hasAnyPlayerRow) {
    return 'Any Player covers that whole position. Change Any to Men or Women to split that position into more rows.'
  }

  return 'All valid position/player group combinations have been added. Increase "Spots" on an existing row to request more subs.'
}
