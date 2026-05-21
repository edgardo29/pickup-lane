import { NeedASubAdditionalInfoSection } from './NeedASubAdditionalInfoSection.jsx'
import { NeedASubGameDetailsSection } from './NeedASubGameDetailsSection.jsx'
import { NeedASubLocationSection } from './NeedASubLocationSection.jsx'
import { NeedASubRequirementsSection } from './NeedASubRequirementsSection.jsx'

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
  return (
    <form className="need-sub-form" onSubmit={onSubmit}>
      <NeedASubGameDetailsSection
        form={form}
        isDateLocked={isDateLocked}
        onUpdateField={onUpdateField}
        onUpdateGamePlayerGroup={onUpdateGamePlayerGroup}
      />
      <NeedASubRequirementsSection
        form={form}
        totalSpotsNeeded={totalSpotsNeeded}
        onAddPosition={onAddPosition}
        onRemovePosition={onRemovePosition}
        onUpdatePosition={onUpdatePosition}
      />
      <NeedASubLocationSection
        form={form}
        onUpdateField={onUpdateField}
      />
      <NeedASubAdditionalInfoSection
        form={form}
        onUpdateField={onUpdateField}
      />

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

export default NeedASubForm
