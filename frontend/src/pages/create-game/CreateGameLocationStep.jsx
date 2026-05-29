import {
  SelectInput,
  StepHeading,
  TextareaInput,
  TextInput,
} from './CreateGameControls.jsx'
import { createGameFieldLimits, US_STATE_OPTIONS } from './createGameData.js'

export function LocationStep({ form, updateField }) {
  return (
    <>
      <StepHeading
        title="Where will you play?"
        text="Add the venue details players will see on the game page."
      />

      <div className="create-game-location-fields">
        <div className="create-game-location-field create-game-location-field--venue">
          <TextInput
            form={form}
            updateField={updateField}
            field="venueName"
            label="Venue name"
            maxLength={createGameFieldLimits.venueName}
          />
        </div>
        <div className="create-game-location-field create-game-location-field--street">
          <TextInput
            form={form}
            updateField={updateField}
            field="street"
            label="Street address"
            maxLength={createGameFieldLimits.street}
          />
        </div>
        <div className="create-game-location-field create-game-location-field--city">
          <TextInput
            form={form}
            updateField={updateField}
            field="city"
            label="City"
            maxLength={createGameFieldLimits.city}
          />
        </div>
        <div className="create-game-location-field create-game-location-field--state">
          <SelectInput
            field="state"
            form={form}
            label="State"
            options={US_STATE_OPTIONS}
            updateField={updateField}
          />
        </div>
        <div className="create-game-location-field create-game-location-field--zip">
          <TextInput
            form={form}
            updateField={updateField}
            field="zip"
            label="ZIP code"
            maxLength={createGameFieldLimits.zip}
          />
        </div>
        <div className="create-game-location-field create-game-location-field--neighborhood">
          <TextInput
            form={form}
            updateField={updateField}
            field="neighborhood"
            label="Neighborhood (optional)"
            maxLength={createGameFieldLimits.neighborhood}
          />
        </div>
      </div>

      <div className="create-game-location-note">
        <TextareaInput
          form={form}
          updateField={updateField}
          field="parkingNote"
          label="Parking note (optional)"
          maxLength={createGameFieldLimits.parkingNote}
          placeholder="Share parking info or nearby options."
        />
      </div>
    </>
  )
}
