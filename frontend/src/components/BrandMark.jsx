import logo from '../assets/logo.png'
import logoNav from '../assets/logo-nav.png'

function BrandMark({ className = '', compact = false }) {
  return (
    <span className={`brand-mark ${compact ? 'brand-mark--compact' : ''} ${className}`}>
      <img src={compact ? logoNav : logo} alt="" className="brand-mark__logo" />
      <span className="brand-mark__wordmark">
        PICKUP <strong>LANE</strong>
      </span>
    </span>
  )
}

export default BrandMark
