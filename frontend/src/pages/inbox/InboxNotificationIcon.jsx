import {
  Bell,
  CalendarDays,
  CalendarX,
  CircleDollarSign,
  ClipboardList,
  Clock3,
  Headphones,
  MapPin,
  Megaphone,
  MessageSquareText,
  ShieldCheck,
  UserPlus,
  UsersRound,
  WalletCards,
} from 'lucide-react'

const ICON_BY_NOTIFICATION_TYPE = {
  account_security: ShieldCheck,
  admin_notice: Megaphone,
  booking_cancelled: CalendarX,
  booking_confirmed: CalendarDays,
  booking_refunded: CircleDollarSign,
  chat_message: MessageSquareText,
  game_cancelled: CalendarX,
  game_host_assigned: ShieldCheck,
  game_host_removed: ShieldCheck,
  game_player_added_by_admin: UsersRound,
  game_player_removed_by_admin: UsersRound,
  game_reminder: Clock3,
  game_roster_update: UsersRound,
  game_updated: CalendarDays,
  host_update: ShieldCheck,
  payment_failed: WalletCards,
  policy_update: Megaphone,
  refund_processed: CircleDollarSign,
  sub_post_canceled: MapPin,
  sub_post_removed: MapPin,
  sub_post_updated: CalendarDays,
  sub_request_canceled_by_owner: ClipboardList,
  sub_request_canceled_by_player: ClipboardList,
  sub_request_confirmed: ClipboardList,
  sub_request_declined: ClipboardList,
  sub_request_received: UserPlus,
  sub_waitlist_promoted_to_pending: Clock3,
  support_reply: Headphones,
  waitlist_expired: Clock3,
  waitlist_joined: Clock3,
  waitlist_promoted: Clock3,
}

const ICON_BY_NAME = {
  Bell,
  CalendarDays,
  CalendarX,
  CircleDollarSign,
  ClipboardList,
  Clock3,
  Headphones,
  MapPin,
  Megaphone,
  MessageSquareText,
  ShieldCheck,
  UserPlus,
  UsersRound,
  WalletCards,
}

const DANGER_NOTIFICATION_TYPES = new Set([
  'booking_cancelled',
  'game_cancelled',
  'game_host_removed',
  'game_player_removed_by_admin',
  'payment_failed',
  'sub_post_canceled',
  'sub_post_removed',
  'sub_request_canceled_by_owner',
  'sub_request_canceled_by_player',
  'sub_request_declined',
  'waitlist_expired',
])

const SUPPORTED_TONES = new Set(['danger', 'default', 'success', 'warning'])

function InboxNotificationIcon({ className = '', notification }) {
  const Icon = ICON_BY_NAME[notification?.icon] || ICON_BY_NOTIFICATION_TYPE[notification?.notification_type] || Bell
  const severity = notification?.severity
  const fallbackTone = DANGER_NOTIFICATION_TYPES.has(notification?.notification_type)
    ? 'danger'
    : 'default'
  const tone = SUPPORTED_TONES.has(severity) ? severity : fallbackTone
  const classNames = ['inbox-notification-icon', `inbox-notification-icon--${tone}`, className]
    .filter(Boolean)
    .join(' ')

  return (
    <span className={classNames} aria-hidden="true">
      <Icon />
    </span>
  )
}

export default InboxNotificationIcon
