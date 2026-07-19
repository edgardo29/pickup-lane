import {
  CircleDollarSign,
  Goal,
  LayoutDashboard,
  Settings,
  UsersRound,
} from 'lucide-react'

export const adminWorkspaceNavGroups = [
  {
    id: 'overview',
    icon: LayoutDashboard,
    label: 'Overview',
    items: [
      {
        label: 'Action Center',
        to: '/admin/action-center',
        end: true,
      },
      {
        label: 'Review Cases',
        to: '/admin/review-cases',
        end: true,
      },
      {
        label: 'Audit Log',
        to: '/admin/audit',
        end: true,
      },
    ],
  },
  {
    id: 'people',
    icon: UsersRound,
    label: 'People',
    items: [
      {
        label: 'Users',
        to: '/admin/users',
        end: true,
      },
      {
        label: 'Staff',
        to: '/admin/users/staff',
        end: true,
      },
    ],
  },
  {
    id: 'games',
    icon: Goal,
    label: 'Games',
    items: [
      {
        label: 'Community Games',
        to: '/admin/community-games',
        end: true,
      },
      {
        label: 'Need a Sub',
        to: '/admin/need-a-sub',
        end: true,
      },
      {
        label: 'Official Games',
        to: '/admin/official-games',
        end: true,
      },
      {
        label: 'Create Official Game',
        to: '/admin/official-games/new',
        end: true,
      },
    ],
  },
  {
    id: 'money',
    icon: CircleDollarSign,
    label: 'Money',
    items: [
      {
        label: 'Money Follow-Up',
        to: '/admin/money/support-flags',
        end: true,
      },
      {
        label: 'Payments',
        to: '/admin/money/payments',
        end: true,
      },
      {
        label: 'Refunds',
        to: '/admin/money/refunds',
        end: true,
      },
      {
        label: 'User Money',
        to: '/admin/money/users',
        end: true,
      },
      {
        label: 'Credits',
        to: '/admin/money/credits',
        end: true,
      },
      {
        label: 'Saved Cards',
        to: '/admin/money/payment-methods',
        end: true,
      },
    ],
  },
  {
    id: 'system',
    icon: Settings,
    label: 'System',
    items: [
      {
        label: 'Notifications',
        to: '/admin/notifications',
        end: true,
      },
      {
        label: 'Platform Notices',
        to: '/admin/platform-notices',
        end: true,
      },
    ],
  },
]

export const adminWorkspaceNavItems = adminWorkspaceNavGroups.flatMap(
  (group) => group.items,
)

export function hasAdminWorkspaceAccess(adminAccess) {
  return adminAccess?.role === 'admin' && adminAccess?.account_status === 'active'
}

export function canAccessAdminWorkspaceItem(item, adminAccess) {
  return Boolean(item) && hasAdminWorkspaceAccess(adminAccess)
}

export function getVisibleAdminWorkspaceNavItems(adminAccess) {
  return hasAdminWorkspaceAccess(adminAccess) ? adminWorkspaceNavItems : []
}

export function getVisibleAdminWorkspaceNavGroups(adminAccess) {
  return adminWorkspaceNavGroups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) =>
        canAccessAdminWorkspaceItem(item, adminAccess),
      ),
    }))
    .filter((group) => group.items.length > 0)
}

export function getDefaultAdminPath(adminAccess) {
  return getVisibleAdminWorkspaceNavItems(adminAccess)[0]?.to || '/admin/sign-in'
}

export function isAdminWorkspaceItemActive(item, pathname) {
  if (item.to === '/admin/users') {
    return (
      pathname === item.to
      || (
        pathname.startsWith('/admin/users/')
        && !pathname.startsWith('/admin/users/staff')
      )
    )
  }

  if (item.to === '/admin/users/staff') {
    return pathname === item.to
  }

  if (item.to === '/admin/review-cases') {
    return pathname === item.to || pathname.startsWith('/admin/review-cases/')
  }

  if (item.to === '/admin/community-games') {
    return pathname === item.to || pathname.startsWith('/admin/community-games/')
  }

  if (item.to === '/admin/need-a-sub') {
    return pathname === item.to || pathname.startsWith('/admin/need-a-sub/')
  }

  if (item.to === '/admin/notifications') {
    return pathname === item.to
  }

  if (item.to === '/admin/platform-notices') {
    return pathname === item.to
  }

  if (item.to === '/admin/official-games') {
    return (
      pathname === item.to
      || (pathname.startsWith('/admin/official-games/') && pathname !== '/admin/official-games/new')
    )
  }

  if (item.to === '/admin/money/support-flags') {
    return pathname === item.to || pathname.startsWith('/admin/money/support-flags/')
  }

  if (item.to === '/admin/money/payments') {
    return pathname === item.to || pathname.startsWith('/admin/money/payments/')
  }

  if (item.to === '/admin/money/refunds') {
    return pathname === item.to || pathname.startsWith('/admin/money/refunds/')
  }

  if (item.to === '/admin/money/credits') {
    return pathname === item.to || pathname.startsWith('/admin/money/credits/')
  }

  if (item.to === '/admin/money/users') {
    return pathname === item.to || pathname.startsWith('/admin/money/users/')
  }

  if (item.to === '/admin/money/payment-methods') {
    return pathname === item.to
  }

  return pathname === item.to
}

export function canAccessAdminPath(pathname, adminAccess) {
  if (!hasAdminWorkspaceAccess(adminAccess)) {
    return false
  }

  const matchedItem = adminWorkspaceNavItems.find((item) =>
    isAdminWorkspaceItemActive(item, pathname),
  )

  return pathname === '/admin' || Boolean(matchedItem)
}
