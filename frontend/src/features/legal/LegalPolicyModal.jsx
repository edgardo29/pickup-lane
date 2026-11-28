import { useLayoutEffect, useRef } from 'react'
import {
  ClipboardCheck,
  FileText,
  ReceiptText,
  ShieldCheck,
  X,
} from 'lucide-react'
import {
  dismissOnBackdropMouseDown,
  useDismissibleModal,
} from '../../hooks/useDismissibleModal.js'
import { getLegalPolicy, LEGAL_POLICY_IDS, LEGAL_POLICIES } from './legalPolicies.js'
import './LegalPolicyModal.css'

const policyIcons = {
  [LEGAL_POLICY_IDS.terms]: FileText,
  [LEGAL_POLICY_IDS.privacy]: ShieldCheck,
  [LEGAL_POLICY_IDS.cancellationRefunds]: ReceiptText,
  [LEGAL_POLICY_IDS.codeOfConduct]: ClipboardCheck,
}

export function LegalPolicyModal({ onClose, policyId }) {
  const policy = getLegalPolicy(policyId) || LEGAL_POLICIES[LEGAL_POLICY_IDS.terms]
  const Icon = policyIcons[policy.id] || FileText
  const titleId = `legal-policy-modal-title-${policy.id}`

  const dialogRef = useRef(null)
  const closeRef = useRef(null)
  useDismissibleModal(onClose)
  useLayoutEffect(() => {
    const opener = document.activeElement
    const dialog = dialogRef.current
    closeRef.current.focus()
    function keepFocus(event) {
      if (!dialog.contains(event.target)) closeRef.current.focus()
    }
    function trapTab(event) {
      if (event.key !== 'Tab') return
      const controls = [...dialog.querySelectorAll('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]')]
      const first = controls[0]
      const last = controls.at(-1)
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('focusin', keepFocus)
    dialog.addEventListener('keydown', trapTab)
    return () => {
      document.removeEventListener('focusin', keepFocus)
      dialog.removeEventListener('keydown', trapTab)
      if (opener?.isConnected) opener.focus()
    }
  }, [policy.id])

  return (
    <div
      ref={dialogRef}
      aria-labelledby={titleId}
      aria-modal="true"
      className="legal-policy-modal-backdrop"
      role="dialog"
      onMouseDown={(event) => dismissOnBackdropMouseDown(event, onClose)}
    >
      <section className="legal-policy-modal">
        <header className="legal-policy-modal__header">
          <div>
            <h2 className="legal-policy-modal__title" id={titleId}>
              <span className="legal-policy-modal__title-icon" aria-hidden="true">
                <Icon />
              </span>
              <span>{policy.title}</span>
            </h2>
            {policy.summary && <p>{policy.summary}</p>}
          </div>

          <button
            ref={closeRef}
            aria-label={`Close ${policy.title}`}
            className="legal-policy-modal__close"
            type="button"
            onClick={onClose}
          >
            <X aria-hidden="true" />
          </button>
        </header>

        <div aria-label={`${policy.title} text`} className="legal-policy-modal__content" role="region" tabIndex={0}>
          {policy.sections.map((section) => (
            <section key={section.title}>
              <h3>{section.title}</h3>
              <p>{section.body}</p>
            </section>
          ))}
        </div>
      </section>
    </div>
  )
}
