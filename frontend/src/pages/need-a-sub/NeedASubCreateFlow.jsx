import { useState } from 'react'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import { NeedASubAdditionalInfoSection } from './NeedASubAdditionalInfoSection.jsx'
import { NeedASubCreatePreview } from './NeedASubCreatePreview.jsx'
import { NeedASubCreateReview } from './NeedASubCreateReview.jsx'
import { NeedASubCreateStepRail } from './NeedASubCreateStepRail.jsx'
import { NeedASubGameDetailsSection } from './NeedASubGameDetailsSection.jsx'
import { NeedASubLocationSection } from './NeedASubLocationSection.jsx'
import { NeedASubRequirementsSection } from './NeedASubRequirementsSection.jsx'
import { getSubPostFlowSteps } from './needASubCreateSteps.js'
import {
  getFirstInvalidNeedASubCreateStep,
  validateNeedASubCreateStep,
} from './needASubValidation.js'

const createStepHeadings = {
  game: {
    title: "Let's start with the game",
    text: 'Add the outside game details subs need to understand the spot.',
  },
  subs: {
    title: 'Who do you need?',
    text: 'Set the player groups and positions you need covered.',
  },
  location: {
    title: 'Where is the game?',
    text: 'Add the venue details subs will use to find the game.',
  },
  notes: {
    title: 'Anything else subs should know?',
    text: 'Share price or context that helps subs show up prepared.',
  },
  review: {
    title: 'Review your sub post',
    text: 'Confirm the details before publishing.',
  },
}

const editStepHeadings = {
  game: {
    title: 'Update the game',
    text: 'Adjust the outside game details subs need to understand the spot.',
  },
  subs: {
    title: 'Update the sub needs',
    text: 'Keep requested rows intact while changing open spots where allowed.',
  },
  location: {
    title: 'Update the location',
    text: 'Edit the venue details subs will use to find the game.',
  },
  notes: {
    title: 'Update notes and payment',
    text: 'Revise price or context that helps subs show up prepared.',
  },
  review: {
    title: 'Review your changes',
    text: 'Confirm the details before saving.',
  },
}

function NeedASubCreateFlow({
  form,
  formError,
  isCreating,
  isDateLocked = false,
  isGamePlayerGroupOptionDisabled = () => false,
  mode = 'create',
  onCancel,
  onAddPosition,
  onCheckDuplicateDate,
  onClearFeedback,
  onRemovePosition,
  onSubmit,
  onUpdateField,
  onUpdateGamePlayerGroup,
  onUpdatePosition,
  submitLabel,
  submittingLabel,
  totalSpotsNeeded,
}) {
  const [activeStep, setActiveStep] = useState(0)
  const [stepError, setStepError] = useState('')
  const [isCheckingDate, setIsCheckingDate] = useState(false)
  const steps = getSubPostFlowSteps(mode)
  const isEditMode = mode === 'edit'
  const isFirstStep = activeStep === 0
  const isPublishStep = activeStep === steps.length - 1
  const activeStepConfig = steps[activeStep]
  const nextStep = steps[activeStep + 1]
  const activeHeading = (isEditMode ? editStepHeadings : createStepHeadings)[activeStepConfig.key]
  const visibleError = stepError || formError
  const finalSubmitLabel = submitLabel || (isEditMode ? 'Save Changes' : 'Publish Post')
  const finalSubmittingLabel = submittingLabel || (isEditMode ? 'Saving...' : 'Publishing...')

  function goBack() {
    setStepError('')
    onClearFeedback?.()
    setActiveStep((currentStep) => Math.max(0, currentStep - 1))
  }

  async function goNext() {
    const error = validateNeedASubCreateStep(activeStepConfig.key, form)
    if (error) {
      setStepError(error)
      return
    }

    if (!isEditMode && activeStepConfig.key === 'game' && onCheckDuplicateDate) {
      setIsCheckingDate(true)

      try {
        const duplicateDateError = await onCheckDuplicateDate()
        if (duplicateDateError) {
          setStepError(duplicateDateError)
          return
        }
      } finally {
        setIsCheckingDate(false)
      }
    }

    setStepError('')
    onClearFeedback?.()
    setActiveStep((currentStep) => Math.min(steps.length - 1, currentStep + 1))
  }

  function preventSubmit(event) {
    event.preventDefault()
  }

  function handlePublish() {
    const invalidStep = getFirstInvalidNeedASubCreateStep(steps, form)
    if (invalidStep.error) {
      setActiveStep(invalidStep.index)
      setStepError(invalidStep.error)
      return
    }

    setStepError('')
    onSubmit()
  }

  function clearLocalError() {
    if (stepError) {
      setStepError('')
    }
  }

  function handleUpdateField(field, value) {
    clearLocalError()
    onUpdateField(field, value)
  }

  function handleUpdateGamePlayerGroup(value) {
    clearLocalError()
    onUpdateGamePlayerGroup(value)
  }

  function handleAddPosition() {
    clearLocalError()
    onAddPosition()
  }

  function handleRemovePosition(index) {
    clearLocalError()
    onRemovePosition(index)
  }

  function handleUpdatePosition(index, field, value) {
    clearLocalError()
    onUpdatePosition(index, field, value)
  }

  function handleCancel() {
    setStepError('')
    onClearFeedback?.()
    onCancel()
  }

  return (
    <form className="need-sub-create-flow" onSubmit={preventSubmit}>
      <NeedASubCreateStepRail
        activeStep={activeStep}
        ariaLabel={isEditMode ? 'Edit Sub Post progress' : 'Create Sub Post progress'}
        steps={steps}
      />

      <section className="need-sub-create-layout">
        <div className="need-sub-create-card">
          <div className="need-sub-create-heading">
            <h2>{activeHeading.title}</h2>
            <p>{activeHeading.text}</p>
          </div>

          {activeStep === 0 && (
            <NeedASubGameDetailsSection
              form={form}
              hideHeading
              isDateLocked={isDateLocked}
              isGamePlayerGroupOptionDisabled={isGamePlayerGroupOptionDisabled}
              splitTimeFields
              onUpdateField={handleUpdateField}
              onUpdateGamePlayerGroup={handleUpdateGamePlayerGroup}
            />
          )}

          {activeStep === 1 && (
            <NeedASubRequirementsSection
              form={form}
              hideTitle
              iconActions
              isEditMode={isEditMode}
              totalSpotsNeeded={totalSpotsNeeded}
              onAddPosition={handleAddPosition}
              onRemovePosition={handleRemovePosition}
              onUpdatePosition={handleUpdatePosition}
            />
          )}

          {activeStep === 2 && (
            <NeedASubLocationSection
              form={form}
              hideHeading
              onUpdateField={handleUpdateField}
            />
          )}

          {activeStep === 3 && (
            <NeedASubAdditionalInfoSection
              form={form}
              hideHeading
              onUpdateField={handleUpdateField}
            />
          )}

          {activeStep === 4 && (
            <NeedASubCreateReview form={form} totalSpotsNeeded={totalSpotsNeeded} />
          )}

          <FormErrorMessage>{visibleError}</FormErrorMessage>

          <div className="need-sub-create-actions">
            <button className="need-sub-form-cancel need-sub-create-cancel" type="button" onClick={handleCancel}>
              Cancel
            </button>
            <div className="need-sub-create-actions__right">
              {!isFirstStep && (
                <button className="need-sub-create-secondary" type="button" onClick={goBack}>
                  Back
                </button>
              )}
              {isPublishStep ? (
                <button
                  className="need-sub-primary need-sub-create-publish"
                  disabled={isCreating}
                  type="button"
                  onClick={handlePublish}
                >
                  {isCreating ? finalSubmittingLabel : finalSubmitLabel}
                  <span aria-hidden="true">→</span>
                </button>
              ) : (
                <button
                  className="need-sub-primary"
                  disabled={isCheckingDate}
                  type="button"
                  onClick={goNext}
                >
                  <span className="need-sub-create-next-label-full">Next: {nextStep.label}</span>
                  <span className="need-sub-create-next-label-short">Next</span>
                  <span aria-hidden="true">→</span>
                </button>
              )}
            </div>
          </div>
        </div>

        <NeedASubCreatePreview
          activeStepKey={activeStepConfig.key}
          form={form}
          totalSpotsNeeded={totalSpotsNeeded}
        />
      </section>
    </form>
  )
}

export default NeedASubCreateFlow
