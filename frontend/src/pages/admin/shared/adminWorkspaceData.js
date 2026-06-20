export const ADMIN_PERMISSIONS = {
  ACTION_CENTER_VIEW: 'admin.action_center.view',
  AUDIT_READ: 'admin.audit.read',
  AUDIT_SUPPORT_READ: 'admin.audit.support_read',
  COMMUNITY_GAMES_CANCEL: 'admin.community_games.cancel',
  CONTENT_MODERATE: 'admin.content.moderate',
  OFFICIAL_GAMES_READ: 'admin.official_games.read',
  OFFICIAL_GAMES_WRITE: 'admin.official_games.write',
  OFFICIAL_GAMES_CANCEL: 'admin.official_games.cancel',
  OFFICIAL_GAMES_ROSTER_MANAGE: 'admin.official_games.roster_manage',
  MONEY_CREDIT_MANAGE: 'admin.money.credit_manage',
  MONEY_READ: 'admin.money.read',
  MONEY_REFUND: 'admin.money.refund',
  USERS_READ: 'admin.users.read',
}

export const adminWorkspaceNavItems = [
  {
    label: 'Action Center',
    to: '/admin/action-center',
    end: true,
    permission: ADMIN_PERMISSIONS.ACTION_CENTER_VIEW,
  },
  {
    label: 'Audit Log',
    to: '/admin/audit',
    end: true,
    permissions: [
      ADMIN_PERMISSIONS.AUDIT_READ,
      ADMIN_PERMISSIONS.AUDIT_SUPPORT_READ,
    ],
  },
  {
    label: 'Official Games',
    to: '/admin/official-games',
    end: true,
    permission: ADMIN_PERMISSIONS.OFFICIAL_GAMES_READ,
  },
  {
    label: 'Create Official Game',
    to: '/admin/official-games/new',
    end: true,
    permission: ADMIN_PERMISSIONS.OFFICIAL_GAMES_WRITE,
  },
  {
    label: 'Money Follow-Up',
    to: '/admin/money/support-flags',
    end: true,
    permission: ADMIN_PERMISSIONS.MONEY_READ,
  },
  {
    label: 'Payments',
    to: '/admin/money/payments',
    end: true,
    permission: ADMIN_PERMISSIONS.MONEY_READ,
  },
  {
    label: 'Refunds',
    to: '/admin/money/refunds',
    end: true,
    permission: ADMIN_PERMISSIONS.MONEY_READ,
  },
  {
    label: 'User Money',
    to: '/admin/money/users',
    end: true,
    permission: ADMIN_PERMISSIONS.MONEY_READ,
  },
  {
    label: 'Credits',
    to: '/admin/money/credits',
    end: true,
    permission: ADMIN_PERMISSIONS.MONEY_READ,
  },
  {
    label: 'Saved Cards',
    to: '/admin/money/payment-methods',
    end: true,
    permission: ADMIN_PERMISSIONS.MONEY_READ,
  },
]

const adminWorkspaceStandalonePathRules = [
  {
    matches: (pathname) => pathname.startsWith('/admin/money/payments/'),
    permission: ADMIN_PERMISSIONS.MONEY_READ,
  },
  {
    matches: (pathname) => pathname.startsWith('/admin/money/refunds/'),
    permission: ADMIN_PERMISSIONS.MONEY_READ,
  },
  {
    matches: (pathname) => pathname.startsWith('/admin/money/credits/'),
    permission: ADMIN_PERMISSIONS.MONEY_READ,
  },
  {
    matches: (pathname) => pathname.startsWith('/admin/money/support-flags/'),
    permission: ADMIN_PERMISSIONS.MONEY_READ,
  },
  {
    matches: (pathname) => pathname.startsWith('/admin/money/users/'),
    permission: ADMIN_PERMISSIONS.MONEY_READ,
  },
]

export function hasAdminPermission(adminAccess, permission) {
  return Boolean(adminAccess?.permissions?.includes(permission))
}

export function hasAnyAdminPermission(adminAccess, permissions) {
  return permissions.some((permission) => hasAdminPermission(adminAccess, permission))
}

function getAdminWorkspaceItemPermissions(item) {
  return item.permissions || [item.permission]
}

export function canAccessAdminWorkspaceItem(item, adminAccess) {
  return hasAnyAdminPermission(adminAccess, getAdminWorkspaceItemPermissions(item))
}

export function getVisibleAdminWorkspaceNavItems(adminAccess) {
  return adminWorkspaceNavItems.filter((item) =>
    canAccessAdminWorkspaceItem(item, adminAccess),
  )
}

export function getDefaultAdminPath(adminAccess) {
  return getVisibleAdminWorkspaceNavItems(adminAccess)[0]?.to || '/admin/sign-in'
}

export function isAdminWorkspaceItemActive(item, pathname) {
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
  if (pathname === '/admin') {
    return getVisibleAdminWorkspaceNavItems(adminAccess).length > 0
  }

  const matchedStandalonePath = adminWorkspaceStandalonePathRules.find((item) =>
    item.matches(pathname),
  )

  if (matchedStandalonePath) {
    return hasAdminPermission(adminAccess, matchedStandalonePath.permission)
  }

  const matchedItem = adminWorkspaceNavItems.find((item) =>
    isAdminWorkspaceItemActive(item, pathname),
  )

  return matchedItem ? canAccessAdminWorkspaceItem(matchedItem, adminAccess) : false
}
