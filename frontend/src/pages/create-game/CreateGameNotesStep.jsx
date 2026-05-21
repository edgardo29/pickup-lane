import {
  PaymentMethodsEditor,
  SectionLabel,
  StepHeading,
  TextareaInput,
} from './CreateGameControls.jsx'

export function NotesStep({ form, updateField }) {
  const isFreeGame = Number(form.price) === 0

  return (
    <>
      <StepHeading
        title="Notes and Payment"
        text="Add anything players should know before they join."
      />

      <div className="create-game-section">
        <SectionLabel>Host Payment</SectionLabel>
        <PaymentMethodsEditor
          allowNoPayment={isFreeGame}
          methods={form.paymentMethods}
          onChange={(methods) => updateField('paymentMethods', methods)}
        />
      </div>

      <TextareaInput
        form={form}
        updateField={updateField}
        field="gameNotes"
        label="Game notes"
        maxLength={200}
        placeholder="Share any important info with players..."
      />
    </>
  )
}
