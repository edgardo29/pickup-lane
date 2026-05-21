import { US_STATE_OPTIONS } from './needASubData.js'
import { NeedASubFormField } from './NeedASubFormField.jsx'

export function NeedASubLocationSection({
  form,
  onUpdateField,
}) {
  return (
    <section className="need-sub-form-section">
      <div className="need-sub-card-heading">
        <p>Location</p>
      </div>

      <div className="need-sub-location-layout">
        <NeedASubFormField label="Venue or park name">
          <input
            placeholder="e.g. Rauner YMCA"
            value={form.locationName}
            onChange={(event) => onUpdateField('locationName', event.target.value)}
          />
        </NeedASubFormField>
        <NeedASubFormField label="Street address">
          <input
            placeholder="e.g. 123 Field Ave"
            value={form.addressLine1}
            onChange={(event) => onUpdateField('addressLine1', event.target.value)}
          />
        </NeedASubFormField>
        <NeedASubFormField label="City">
          <input value={form.city} onChange={(event) => onUpdateField('city', event.target.value)} />
        </NeedASubFormField>
        <div className="need-sub-location-pair">
          <NeedASubFormField label="State">
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
          <NeedASubFormField label="ZIP">
            <input
              value={form.postalCode}
              onChange={(event) => onUpdateField('postalCode', event.target.value)}
            />
          </NeedASubFormField>
        </div>
        <NeedASubFormField label="Neighborhood (optional)">
          <input
            placeholder="e.g. Pilsen"
            value={form.neighborhood}
            onChange={(event) => onUpdateField('neighborhood', event.target.value)}
          />
        </NeedASubFormField>
      </div>
    </section>
  )
}
