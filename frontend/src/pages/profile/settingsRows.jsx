import {
  ShieldCheckIcon,
  UserIcon,
} from '../../components/BrowseIcons.jsx'
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
  getFullName,
} from './profileFormatters.js'

export function buildSettingsRows({
  canAddPassword,
  currentUser,
  defaultPaymentMethod,
  navigate,
  notificationSummary,
  onOpenDelete,
  onOpenNotifications,
  onOpenPassword,
  logout,
}) {
  return {
    accountAccessRows: buildAccountAccessRows({ canAddPassword, onOpenPassword }),
    accountDetailRows: buildAccountDetailRows({ currentUser }),
    accountRows: buildAccountRows({ logout, navigate, onOpenDelete }),
    preferenceRows: buildPreferenceRows({
      defaultPaymentMethod,
      notificationSummary,
      onOpenNotifications,
    }),
  }
}

function buildAccountDetailRows({ currentUser }) {
  return [
    {
      icon: <UserIcon />,
      title: getFullName(currentUser),
      text: currentUser?.email,
      state: { from: '/settings', fromLabel: 'Back to settings' },
      to: '/profile/edit',
    },
  ]
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
    },
    {
      icon: <HelpIcon />,
      title: 'Help & Support',
      text: 'FAQ, support, and contact us',
    },
    {
      icon: <DocumentIcon />,
      title: 'Terms & Conditions',
      text: 'Read our terms of service',
      to: '/terms',
      state: { from: '/settings', fromLabel: 'Back to Settings' },
    },
    {
      icon: <ShieldCheckIcon />,
      title: 'Privacy Policy',
      text: 'How we handle your data',
      to: '/privacy',
      state: { from: '/settings', fromLabel: 'Back to Settings' },
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
