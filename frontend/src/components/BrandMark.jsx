import logo from '../assets/logo.png'
import logoNav from '../assets/logo-nav.png'

function BrandMark({ className = '', compact = false, croppedMark = false }) {
  const useNavLogo = compact || croppedMark
  const logoSrc = useNavLogo ? logoNav : logo
  const logoSize = useNavLogo
    ? { width: 614, height: 538 }
    : { width: 1254, height: 1254 }

  return (
    <span className={`brand-mark ${compact ? 'brand-mark--compact' : ''} ${className}`}>
      <img
        src={logoSrc}
        alt=""
        className="brand-mark__logo"
        width={logoSize.width}
        height={logoSize.height}
        decoding="async"
      />
      <span className="brand-mark__wordmark">
        PICKUP <strong>LANE</strong>
      </span>
    </span>
  )
}

export default BrandMark
