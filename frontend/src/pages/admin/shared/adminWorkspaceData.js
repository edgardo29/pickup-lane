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

  return pathname === item.to
}

export function canAccessAdminPath(pathname, adminAccess) {
  if (pathname === '/admin') {
    return getVisibleAdminWorkspaceNavItems(adminAccess).length > 0
  }

  const matchedItem = adminWorkspaceNavItems.find((item) =>
    isAdminWorkspaceItemActive(item, pathname),
  )

  return matchedItem ? canAccessAdminWorkspaceItem(matchedItem, adminAccess) : false
}
