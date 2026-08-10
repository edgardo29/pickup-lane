import { useContext } from 'react'
import { StepUpContext } from '../context/stepUpContext.js'

export function useStepUp() {
  const context = useContext(StepUpContext)
  if (!context) {
    throw new Error('useStepUp must be used within a StepUpProvider.')
  }

  return context
}
