import { CircleHelp, Info } from 'lucide-react'
import { HostPaymentSection } from './GameDetailsHostPayment.jsx'

export function SidebarAboutSection({ aboutText, hostPaymentMethods }) {
  return (
    <div className="details-sidebar-section">
      <h2 className="details-section-heading">
        <span className="details-section-icon">
          <Info />
        </span>
        About This Game
      </h2>
      <p>{aboutText}</p>

      {hostPaymentMethods.length > 0 && (
        <HostPaymentSection methods={hostPaymentMethods} />
      )}
    </div>
  )
}

export function SidebarQuestionsSection() {
  return (
    <div className="details-sidebar-section">
      <h2 className="details-section-heading">
        <span className="details-section-icon">
          <CircleHelp />
        </span>
        Questions?
      </h2>
      <p>Check out our Help Center or contact our support team.</p>

      <a className="details-help-button" href="mailto:support@pickuplane.local">
        Visit Help Center
      </a>
    </div>
  )
}
