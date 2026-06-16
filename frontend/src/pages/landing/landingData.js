import {
  CalendarCheck,
  CheckCircle2,
  Search,
  ShieldCheck,
  UserPlus,
  UsersRound,
} from 'lucide-react'

export const howItWorksSteps = [
  {
    title: 'Find a real game',
    description:
      'Browse soccer games by date, venue, format, skill level, price, and open spots.',
    icon: Search,
    metric: '01',
  },
  {
    title: 'Reserve your spot',
    description:
      'Create an account, review the details, join instantly, or waitlist when a game fills.',
    icon: CalendarCheck,
    metric: '02',
  },
  {
    title: 'Arrive ready',
    description:
      'Get the address, game notes, roster updates, and chat so game day feels organized.',
    icon: CheckCircle2,
    metric: '03',
  },
]

export const waysToPlay = [
  {
    title: 'Official Games',
    eyebrow: 'Curated runs',
    description:
      'Pickup Lane posts official games at approved venues with clear details, rosters, and checkout.',
    icon: ShieldCheck,
  },
  {
    title: 'Community Hosted',
    eyebrow: 'Player-led',
    description:
      'Players can create games, set the format and rules, and manage the roster from one place.',
    icon: UsersRound,
  },
  {
    title: 'Need a Sub',
    eyebrow: 'Open spots',
    description:
      'Post a missing player or request a spot when someone needs a replacement for an upcoming game.',
    icon: UserPlus,
  },
]

export const hostFlowItems = [
  'Choose the venue, date, time, format, price, and skill level.',
  'Publish the game and let players reserve available spots.',
  'Manage the roster, waitlist, guests, chat, edits, and cancellations.',
]

export const subFlowItems = [
  'Post the exact open spots you need filled.',
  'Review incoming player requests before confirming anyone.',
  'Keep confirmed subs aligned with game details and chat.',
]

export const faqs = [
  {
    question: 'Do I need an account to join a game?',
    answer:
      'You can browse games without an account, but you will need one to reserve a spot, manage bookings, or host.',
  },
  {
    question: 'What happens if a game is full?',
    answer:
      'Join the waitlist when available. If a spot opens, the game can promote players from the waitlist.',
  },
  {
    question: 'Can I bring guests?',
    answer:
      'Some games support guests. When they do, the game details and checkout flow show the available guest options.',
  },
  {
    question: 'Can I host my own game?',
    answer:
      'Yes. Signed-in players can create community games, set the key details, and manage the roster.',
  },
  {
    question: 'What is Need a Sub?',
    answer:
      'Need a Sub helps players fill specific open spots when someone cannot make a game.',
  },
  {
    question: 'Are payments secure?',
    answer:
      'Payment collection uses Stripe, and Pickup Lane does not store raw card numbers on its own servers.',
  },
]
