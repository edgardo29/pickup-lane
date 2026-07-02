import { ShieldCheckIcon } from '../../components/BrowseIcons.jsx'
import { LEGAL_POLICY_IDS } from '../../features/legal/legalPolicies.js'
import {
  BellIcon,
  DocumentIcon,
  HelpIcon,
  KeyIcon,
  LogoutIcon,
  PaymentCardIcon,
  TrashIcon,
} from './ProfileIcons.jsx'
import {
  capitalize,
} from './profileFormatters.js'

export function buildSettingsRows({
  canAddPassword,
  defaultPaymentMethod,
  navigate,
  notificationSummary,
  onOpenLegalPolicy,
  onOpenDelete,
  onOpenNotifications,
  onOpenPassword,
  logout,
}) {
  return {
    accountAccessRows: buildAccountAccessRows({ canAddPassword, onOpenPassword }),
    accountRows: buildAccountRows({ logout, navigate, onOpenDelete }),
    preferenceRows: buildPreferenceRows({
      defaultPaymentMethod,
      notificationSummary,
      onOpenNotifications,
    }),
    supportRows: buildSupportRows({ onOpenLegalPolicy }),
  }
}

function buildPreferenceRows({
  defaultPaymentMethod,
  notificationSummary,
  onOpenNotifications,
}) {
  return [
    {
      icon: <BellIcon />,
      title: 'Notifications',
      text: notificationSummary,
      onClick: onOpenNotifications,
    },
    {
      icon: <PaymentCardIcon />,
      title: 'Payment Methods',
      text: defaultPaymentMethod
        ? `${capitalize(defaultPaymentMethod.card_brand)} ending ${defaultPaymentMethod.card_last4}`
        : 'No card on file',
      to: '/profile/payment-methods',
    },
  ]
}

function buildSupportRows({ onOpenLegalPolicy }) {
  return [
    {
      icon: <HelpIcon />,
      title: 'Help & Support',
      text: 'FAQ, support, and contact us',
    },
    {
      icon: <DocumentIcon />,
      title: 'Terms & Conditions',
      text: 'Read our terms of service',
      onClick: () => onOpenLegalPolicy(LEGAL_POLICY_IDS.terms),
    },
    {
      icon: <ShieldCheckIcon />,
      title: 'Privacy Policy',
      text: 'How we handle your data',
      onClick: () => onOpenLegalPolicy(LEGAL_POLICY_IDS.privacy),
    },
  ]
}

function buildAccountAccessRows({ canAddPassword, onOpenPassword }) {
  return canAddPassword
    ? [
        {
          icon: <KeyIcon />,
          title: 'Add Password',
          text: 'Sign in with email and password too',
          onClick: onOpenPassword,
        },
      ]
    : []
}

function buildAccountRows({ logout, navigate, onOpenDelete }) {
  return [
    {
      icon: <LogoutIcon />,
      title: 'Log Out',
      text: 'Sign out of this device',
      onClick: async () => {
        await logout()
        navigate('/')
      },
    },
    {
      icon: <TrashIcon />,
      title: 'Delete Account',
      text: 'Permanently delete your account',
      tone: 'danger',
      onClick: onOpenDelete,
    },
  ]
}
