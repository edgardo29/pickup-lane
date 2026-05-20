import {
  ENVIRONMENT_OPTIONS,
  FORMAT_OPTIONS,
  GROUP_OPTIONS,
  MIN_DATE_VALUE,
  MAX_SUB_ROWS,
  MAX_TOTAL_SUBS,
  POSITION_OPTIONS,
  SKILL_OPTIONS,
  US_STATE_OPTIONS,
  getMaxPositionRows,
  TIME_OPTIONS,
  getPositionGroupOptions,
} from './needASubData.js'

function NeedASubForm({
  form,
  formError,
  isDateLocked = false,
  isSaving,
  onCancel = null,
  onAddPosition,
  onRemovePosition,
  onSubmit,
  onUpdateField,
  onUpdateGamePlayerGroup,
  onUpdatePosition,
  submitLabel = 'Publish Post',
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
    <form className="need-sub-form" onSubmit={onSubmit}>
      <section className="need-sub-form-section">
        <div className="need-sub-card-heading">
          <p>Game Details</p>
        </div>

        <div className="need-sub-game-layout">
          <Field label="Date" className="need-sub-field--date">
            <input
              disabled={isDateLocked}
              min={MIN_DATE_VALUE}
              type="date"
              value={form.date}
              onChange={(event) => onUpdateField('date', event.target.value)}
            />
          </Field>

          <div className="need-sub-field need-sub-field--time">
            <span>Time</span>
            <div className="need-sub-time-pair">
              <select
                aria-label="Start time"
                value={form.startTime}
                onChange={(event) => onUpdateField('startTime', event.target.value)}
              >
                {TIME_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
              <select
                aria-label="End time"
                value={form.endTime}
                onChange={(event) => onUpdateField('endTime', event.target.value)}
              >
                {TIME_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </div>
          </div>

          <Field label="Format" className="need-sub-field--format">
            <select
              value={form.formatLabel}
              onChange={(event) => onUpdateField('formatLabel', event.target.value)}
            >
              {FORMAT_OPTIONS.map((format) => (
                <option key={format} value={format}>{format}</option>
              ))}
            </select>
          </Field>
          <Field label="Indoor / Outdoor" className="need-sub-field--environment">
            <select
              required
              value={form.environment}
              onChange={(event) => onUpdateField('environment', event.target.value)}
            >
              <option value="">Select</option>
              {ENVIRONMENT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </Field>
          <Field label="Skill level" className="need-sub-field--skill">
            <select
              value={form.skillLevel}
              onChange={(event) => onUpdateField('skillLevel', event.target.value)}
            >
              {SKILL_OPTIONS.map((skill) => (
                <option key={skill.value} value={skill.value}>{skill.label}</option>
              ))}
            </select>
          </Field>
          <Field label="Player group" className="need-sub-field--group">
            <select
              value={form.gamePlayerGroup}
              onChange={(event) => onUpdateGamePlayerGroup(event.target.value)}
            >
              {GROUP_OPTIONS.map((group) => (
                <option key={group.value} value={group.value}>{group.label}</option>
              ))}
            </select>
          </Field>
        </div>
      </section>

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
                <Field label="Position">
                  <select
                    value={position.position_label}
                    onChange={(event) => onUpdatePosition(index, 'position_label', event.target.value)}
                  >
                    {POSITION_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Player Type">
                  <select
                    value={position.player_group}
                    onChange={(event) => onUpdatePosition(index, 'player_group', event.target.value)}
                  >
                    {playerGroupOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Spots">
                  <select
                    value={position.spots_needed}
                    onChange={(event) => onUpdatePosition(index, 'spots_needed', event.target.value)}
                  >
                    {getSpotOptions(position.spots_needed, totalSpotsNeeded).map((spotCount) => (
                      <option key={spotCount} value={spotCount}>{spotCount}</option>
                    ))}
                  </select>
                </Field>
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

      <section className="need-sub-form-section">
        <div className="need-sub-card-heading">
          <p>Location</p>
        </div>

        <div className="need-sub-location-layout">
          <Field label="Venue or park name">
            <input
              placeholder="e.g. Rauner YMCA"
              value={form.locationName}
              onChange={(event) => onUpdateField('locationName', event.target.value)}
            />
          </Field>
          <Field label="Street address">
            <input
              placeholder="e.g. 123 Field Ave"
              value={form.addressLine1}
              onChange={(event) => onUpdateField('addressLine1', event.target.value)}
            />
          </Field>
          <Field label="City">
            <input value={form.city} onChange={(event) => onUpdateField('city', event.target.value)} />
          </Field>
          <div className="need-sub-location-pair">
            <Field label="State">
              <select
                required
                value={form.state}
                onChange={(event) => onUpdateField('state', event.target.value)}
              >
                <option value="">Select</option>
                {US_STATE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </Field>
            <Field label="ZIP">
              <input
                value={form.postalCode}
                onChange={(event) => onUpdateField('postalCode', event.target.value)}
              />
            </Field>
          </div>
          <Field label="Neighborhood (optional)">
            <input
              placeholder="e.g. Pilsen"
              value={form.neighborhood}
              onChange={(event) => onUpdateField('neighborhood', event.target.value)}
            />
          </Field>
        </div>
      </section>

      <section className="need-sub-form-section">
        <div className="need-sub-card-heading">
          <p>Additional Info</p>
        </div>

        <div className="need-sub-price-field">
          <Field label="Price due at venue (optional)">
            <input
              inputMode="decimal"
              placeholder="Free"
              type="text"
              value={form.priceDue}
              onChange={(event) => onUpdateField('priceDue', event.target.value)}
            />
          </Field>
        </div>

        <label className="need-sub-textarea">
          <span>Notes (optional)</span>
          <textarea
            maxLength={500}
            placeholder="e.g. Bring a dark shirt. Ask for Luis at the south entrance."
            value={form.notes}
            onChange={(event) => onUpdateField('notes', event.target.value)}
          />
          <small>{form.notes.length}/500</small>
        </label>
      </section>

      <div className="need-sub-form-actions">
        {formError && <div className="need-sub-form-error">{formError}</div>}
        {onCancel && (
          <button className="need-sub-form-cancel" type="button" onClick={onCancel}>
            Cancel
          </button>
        )}
        <button className="need-sub-primary" disabled={isSaving} type="submit">
          {isSaving ? 'Saving...' : submitLabel}
        </button>
      </div>
    </form>
  )
}

function getSpotOptions(currentSpots, totalSpotsNeeded) {
  const current = Math.max(1, Number(currentSpots || 1))
  const remaining = Math.max(0, MAX_TOTAL_SUBS - Number(totalSpotsNeeded || 0))
  const maxForRow = Math.min(MAX_TOTAL_SUBS, Math.max(current, current + remaining))

  return Array.from({ length: maxForRow }, (_, index) => index + 1)
}

function Field({ children, className = '', label }) {
  return (
    <label className={`need-sub-field ${className}`.trim()}>
      <span>{label}</span>
      {children}
    </label>
  )
}

export default NeedASubForm
