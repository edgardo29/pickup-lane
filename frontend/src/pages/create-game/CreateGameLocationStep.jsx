import {
  SelectInput,
  StepHeading,
  TextareaInput,
  TextInput,
} from './CreateGameControls.jsx'
import { US_STATE_OPTIONS } from './createGameData.js'

export function LocationStep({ form, updateField }) {
  return (
    <>
      <StepHeading
        title="Where will you play?"
        text="Add the venue details players will see on the game page."
      />

      <div className="create-game-grid create-game-grid--single">
        <TextInput
          form={form}
          updateField={updateField}
          field="venueName"
          label="Venue name"
          placeholder="e.g. Brooklyn Sports Hub"
        />
        <TextInput
          form={form}
          updateField={updateField}
          field="street"
          label="Street address"
          placeholder="160 5th St"
        />
      </div>

      <div className="create-game-grid create-game-grid--two">
        <TextInput form={form} updateField={updateField} field="city" label="City" placeholder="Brooklyn" />
        <SelectInput
          field="state"
          form={form}
          label="State"
          options={US_STATE_OPTIONS}
          updateField={updateField}
        />
        <TextInput form={form} updateField={updateField} field="zip" label="ZIP code" placeholder="11215" />
        <TextInput
          form={form}
          updateField={updateField}
          field="neighborhood"
          label="Neighborhood (optional)"
          placeholder="Park Slope"
        />
      </div>

      <div className="create-game-divider" />

      <TextareaInput
        form={form}
        updateField={updateField}
        field="parkingNote"
        label="Parking note (optional)"
        maxLength={120}
        placeholder="Share parking info or nearby options."
      />
    </>
  )
}
