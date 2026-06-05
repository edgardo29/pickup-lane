import {
  ENVIRONMENT_OPTIONS,
  FORMAT_OPTIONS,
  GROUP_OPTIONS,
  MIN_DATE_VALUE,
  SKILL_OPTIONS,
  TIME_OPTIONS,
} from './needASubData.js'
import { NeedASubFormField } from './NeedASubFormField.jsx'

export function NeedASubGameDetailsSection({
  form,
  hideHeading = false,
  isDateLocked,
  isGamePlayerGroupOptionDisabled = () => false,
  onUpdateField,
  onUpdateGamePlayerGroup,
  splitTimeFields = false,
}) {
  return (
    <section className="need-sub-form-section">
      {!hideHeading && (
        <div className="need-sub-card-heading">
          <p>Game Details</p>
        </div>
      )}

      <div className="need-sub-game-layout">
        <NeedASubFormField label="Date" className="need-sub-field--date">
          <input
            disabled={isDateLocked}
            min={MIN_DATE_VALUE}
            type="date"
            value={form.date}
            onChange={(event) => onUpdateField('date', event.target.value)}
          />
        </NeedASubFormField>

        {splitTimeFields ? (
          <>
            <NeedASubFormField label="Start time" className="need-sub-field--start-time">
              <select
                aria-label="Start time"
                value={form.startTime}
                onChange={(event) => onUpdateField('startTime', event.target.value)}
              >
                {TIME_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </NeedASubFormField>
            <NeedASubFormField label="End time" className="need-sub-field--end-time">
              <select
                aria-label="End time"
                value={form.endTime}
                onChange={(event) => onUpdateField('endTime', event.target.value)}
              >
                {TIME_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </NeedASubFormField>
          </>
        ) : (
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
        )}

        <NeedASubFormField label="Format" className="need-sub-field--format">
          <select
            value={form.formatLabel}
            onChange={(event) => onUpdateField('formatLabel', event.target.value)}
          >
            <option value="">Select</option>
            {FORMAT_OPTIONS.map((format) => (
              <option key={format} value={format}>{format}</option>
            ))}
          </select>
        </NeedASubFormField>
        <NeedASubFormField label="Indoor/Outdoor" className="need-sub-field--environment">
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
        </NeedASubFormField>
        <NeedASubFormField label="Skill level" className="need-sub-field--skill">
          <select
            value={form.skillLevel}
            onChange={(event) => onUpdateField('skillLevel', event.target.value)}
          >
            <option value="">Select</option>
            {SKILL_OPTIONS.map((skill) => (
              <option key={skill.value} value={skill.value}>{skill.label}</option>
            ))}
          </select>
        </NeedASubFormField>
        <NeedASubFormField label="Player group" className="need-sub-field--group">
          <select
            value={form.gamePlayerGroup}
            onChange={(event) => onUpdateGamePlayerGroup(event.target.value)}
          >
            <option value="">Select</option>
            {GROUP_OPTIONS.map((group) => (
              <option
                disabled={isGamePlayerGroupOptionDisabled(group.value)}
                key={group.value}
                value={group.value}
              >
                {group.label}
              </option>
            ))}
          </select>
        </NeedASubFormField>
      </div>
    </section>
  )
}
