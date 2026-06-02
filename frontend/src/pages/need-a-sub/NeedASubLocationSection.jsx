import { US_STATE_OPTIONS, needASubFieldLimits } from './needASubData.js'
import { NeedASubFormField } from './NeedASubFormField.jsx'

export function NeedASubLocationSection({
  form,
  hideHeading = false,
  onUpdateField,
}) {
  return (
    <section className="need-sub-form-section">
      {!hideHeading && (
        <div className="need-sub-card-heading">
          <p>Location</p>
        </div>
      )}

      <div className="need-sub-location-layout">
        <NeedASubFormField className="need-sub-location-field need-sub-location-field--venue" label="Venue name">
          <input
            maxLength={needASubFieldLimits.locationName}
            value={form.locationName}
            onChange={(event) => onUpdateField('locationName', event.target.value)}
          />
        </NeedASubFormField>
        <NeedASubFormField className="need-sub-location-field need-sub-location-field--street" label="Street address">
          <input
            maxLength={needASubFieldLimits.addressLine1}
            value={form.addressLine1}
            onChange={(event) => onUpdateField('addressLine1', event.target.value)}
          />
        </NeedASubFormField>
        <NeedASubFormField className="need-sub-location-field need-sub-location-field--city" label="City">
          <input
            maxLength={needASubFieldLimits.city}
            value={form.city}
            onChange={(event) => onUpdateField('city', event.target.value)}
          />
        </NeedASubFormField>
        <NeedASubFormField className="need-sub-location-field need-sub-location-field--state" label="State">
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
        </NeedASubFormField>
        <NeedASubFormField className="need-sub-location-field need-sub-location-field--zip" label="ZIP">
          <input
            maxLength={needASubFieldLimits.postalCode}
            value={form.postalCode}
            onChange={(event) => onUpdateField('postalCode', event.target.value)}
          />
        </NeedASubFormField>
        <NeedASubFormField className="need-sub-location-field need-sub-location-field--neighborhood" label="Neighborhood (optional)">
          <input
            maxLength={needASubFieldLimits.neighborhood}
            value={form.neighborhood}
            onChange={(event) => onUpdateField('neighborhood', event.target.value)}
          />
        </NeedASubFormField>
      </div>
    </section>
  )
}
