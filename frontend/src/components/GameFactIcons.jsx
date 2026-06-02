import {
  Building2,
  CalendarDays,
  CarFront,
  CircleDollarSign,
  CircleUserRound,
  ClipboardList,
  Clock3,
  Grid3X3,
  MapPin,
  MapPinned,
  MessageSquareText,
  ShieldCheck,
  Signal,
  SunMedium,
  Timer,
  UsersRound,
  VenusAndMars,
  WalletCards,
  Warehouse,
} from 'lucide-react'

function GoalkeeperGloveIcon(props) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      viewBox="0 0 24 24"
      {...props}
    >
      <path d="M6.2 10V6.5a1.45 1.45 0 0 1 2.9 0V10" />
      <path d="M9.1 9.7V5.8a1.45 1.45 0 0 1 2.9 0v3.9" />
      <path d="M12 9.7V6.2a1.45 1.45 0 0 1 2.9 0v4.1" />
      <path d="M14.9 10.6V7.7a1.45 1.45 0 0 1 2.9 0v5.6c0 3.8-2.4 6.1-6 6.1h-1.2c-2.7 0-4.7-1.3-5.7-3.6l-1.1-2.5a1.55 1.55 0 0 1 2.7-1.5l2 2.8" />
      <path d="M7.2 21h8.4" />
    </svg>
  )
}

function SoccerBallIcon(props) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      viewBox="0 0 24 24"
      {...props}
    >
      <circle cx="12" cy="12" r="9" />
      <path d="m12 7 4 3-1.5 4.6h-5L8 10Z" />
      <path d="m12 7 .3-4" />
      <path d="m8 10-3.8-1.2" />
      <path d="m9.5 14.6-2.3 3.2" />
      <path d="m14.5 14.6 2.3 3.2" />
      <path d="m16 10 3.8-1.2" />
    </svg>
  )
}

export const AddressIcon = MapPin
export const GameDateIcon = CalendarDays
export const GameDurationIcon = Timer
export const GameEnvironmentIcon = Warehouse
export const GameFormatIcon = Grid3X3
export const GameIndoorIcon = Warehouse
export const GameNotesIcon = MessageSquareText
export const GameOutdoorIcon = SunMedium
export const GamePlayerGroupIcon = VenusAndMars
export const GameSkillIcon = Signal
export const GameSpotsIcon = UsersRound
export const GameStatusIcon = ShieldCheck
export const GameTimeIcon = Clock3
export const GameTraitIcon = SoccerBallIcon
export const GameTypeIcon = Grid3X3
export const HostPaymentIcon = WalletCards
export const HostRulesIcon = ClipboardList
export const NeighborhoodIcon = MapPinned
export const NeedSubFieldPlayersIcon = CircleUserRound
export const NeedSubGoalkeeperIcon = GoalkeeperGloveIcon
export const ParkingIcon = CarFront
export const PlayersIcon = UsersRound
export const PriceIcon = CircleDollarSign
export const SinglePlayerIcon = CircleUserRound
export const VenueIcon = Building2
