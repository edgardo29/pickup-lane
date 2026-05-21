import { NavLink } from 'react-router-dom'
import logoNav from '../../assets/logo-nav.png'

export function AppNavBrand() {
  return (
    <NavLink className="app-nav__brand" to="/" aria-label="Pickup Lane home">
      <span className="app-nav__brand-logo" aria-hidden="true">
        <img src={logoNav} alt="" />
      </span>
      <span className="app-nav__brand-wordmark">
        PICKUP <strong>LANE</strong>
      </span>
    </NavLink>
  )
}
