import {
  PaymentMethodsEditor,
  StepHeading,
  TextareaInput,
} from './CreateGameControls.jsx'
import { createGameFieldLimits } from './createGameData.js'

export function NotesStep({ form, updateField }) {
  const isFreeGame = Number(form.price) === 0

  return (
    <>
      <StepHeading
        title="Notes and Payment"
        text="Add anything players should know before they join."
      />

      <div className="create-game-notes-layout">
        <section className="create-game-notes-section create-game-notes-fields">
          <TextareaInput
            form={form}
            updateField={updateField}
            field="gameNotes"
            label="Game notes (optional)"
            maxLength={createGameFieldLimits.gameNotes}
            placeholder="Share any important info with players."
          />
          <TextareaInput
            form={form}
            updateField={updateField}
            field="hostRules"
            label="Host rules (optional)"
            maxLength={createGameFieldLimits.hostRules}
            placeholder="Share any attendance, cancellation, or player expectations."
          />
        </section>

        <section className="create-game-notes-section create-game-notes-section--payment">
          <PaymentMethodsEditor
            allowNoPayment={isFreeGame}
            methods={form.paymentMethods}
            onChange={(methods) => updateField('paymentMethods', methods)}
          />
        </section>
      </div>
    </>
  )
}
