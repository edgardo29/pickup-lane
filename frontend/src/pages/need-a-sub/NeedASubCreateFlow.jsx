import { useState } from 'react'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import { NeedASubAdditionalInfoSection } from './NeedASubAdditionalInfoSection.jsx'
import { NeedASubCreatePreview } from './NeedASubCreatePreview.jsx'
import { NeedASubCreateReview } from './NeedASubCreateReview.jsx'
import { NeedASubCreateStepRail } from './NeedASubCreateStepRail.jsx'
import { NeedASubGameDetailsSection } from './NeedASubGameDetailsSection.jsx'
import { NeedASubLocationSection } from './NeedASubLocationSection.jsx'
import { NeedASubRequirementsSection } from './NeedASubRequirementsSection.jsx'
import { createSubPostSteps } from './needASubCreateSteps.js'
import {
  getFirstInvalidNeedASubCreateStep,
  validateNeedASubCreateStep,
} from './needASubValidation.js'

const stepHeadings = {
  game: {
    title: "Let's start with the game",
    text: 'Add the outside game details subs need to understand the spot.',
  },
  subs: {
    title: 'Who do you need?',
    text: 'Set the player types and positions you need covered.',
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

function NeedASubCreateFlow({
  form,
  formError,
  isCreating,
  onCancel,
  onAddPosition,
  onRemovePosition,
  onSubmit,
  onUpdateField,
  onUpdateGamePlayerGroup,
  onUpdatePosition,
  totalSpotsNeeded,
}) {
  const [activeStep, setActiveStep] = useState(0)
  const [stepError, setStepError] = useState('')
  const isFirstStep = activeStep === 0
  const isPublishStep = activeStep === createSubPostSteps.length - 1
  const activeStepConfig = createSubPostSteps[activeStep]
  const nextStep = createSubPostSteps[activeStep + 1]
  const activeHeading = stepHeadings[activeStepConfig.key]
  const visibleError = stepError || formError

  function goBack() {
    setStepError('')
    setActiveStep((currentStep) => Math.max(0, currentStep - 1))
  }

  function goNext() {
    const error = validateNeedASubCreateStep(activeStepConfig.key, form)
    if (error) {
      setStepError(error)
      return
    }

    setStepError('')
    setActiveStep((currentStep) => Math.min(createSubPostSteps.length - 1, currentStep + 1))
  }

  function preventSubmit(event) {
    event.preventDefault()
  }

  function handlePublish() {
    const invalidStep = getFirstInvalidNeedASubCreateStep(createSubPostSteps, form)
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
    onCancel()
  }

  return (
    <form className="need-sub-create-flow" onSubmit={preventSubmit}>
      <NeedASubCreateStepRail activeStep={activeStep} />

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
              isDateLocked={false}
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
                  {isCreating ? 'Publishing...' : 'Publish Post'}
                  <span aria-hidden="true">→</span>
                </button>
              ) : (
                <button className="need-sub-primary" type="button" onClick={goNext}>
                  <span className="need-sub-create-next-label-full">Next: {nextStep.label}</span>
                  <span className="need-sub-create-next-label-short">Next</span>
                  <span aria-hidden="true">→</span>
                </button>
              )}
            </div>
          </div>
        </div>

        <NeedASubCreatePreview form={form} totalSpotsNeeded={totalSpotsNeeded} />
      </section>
    </form>
  )
}

export default NeedASubCreateFlow
