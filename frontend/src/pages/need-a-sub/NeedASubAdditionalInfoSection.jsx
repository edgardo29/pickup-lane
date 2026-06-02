import { needASubFieldLimits } from './needASubData.js'
import { NeedASubFormField } from './NeedASubFormField.jsx'

export function NeedASubAdditionalInfoSection({
  form,
  hideHeading = false,
  onUpdateField,
}) {
  return (
    <section className="need-sub-form-section">
      {!hideHeading && (
        <div className="need-sub-card-heading">
          <p>Additional Info</p>
        </div>
      )}

      <div className="need-sub-price-field">
        <NeedASubFormField label="Price due at venue (optional)">
          <input
            inputMode="decimal"
            maxLength={needASubFieldLimits.priceDue}
            type="text"
            value={form.priceDue}
            onChange={(event) => onUpdateField('priceDue', event.target.value)}
          />
        </NeedASubFormField>
      </div>

      <label className="need-sub-textarea">
        <span>Notes (optional)</span>
        <textarea
          maxLength={needASubFieldLimits.notes}
          value={form.notes}
          onChange={(event) => onUpdateField('notes', event.target.value)}
        />
        <small>{form.notes.length}/{needASubFieldLimits.notes}</small>
      </label>
    </section>
  )
}
