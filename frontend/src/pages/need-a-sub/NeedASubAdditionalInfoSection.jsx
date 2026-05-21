import { NeedASubFormField } from './NeedASubFormField.jsx'

export function NeedASubAdditionalInfoSection({
  form,
  onUpdateField,
}) {
  return (
    <section className="need-sub-form-section">
      <div className="need-sub-card-heading">
        <p>Additional Info</p>
      </div>

      <div className="need-sub-price-field">
        <NeedASubFormField label="Price due at venue (optional)">
          <input
            inputMode="decimal"
            placeholder="Free"
            type="text"
            value={form.priceDue}
            onChange={(event) => onUpdateField('priceDue', event.target.value)}
          />
        </NeedASubFormField>
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
  )
}
