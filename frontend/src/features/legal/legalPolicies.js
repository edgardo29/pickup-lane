export const LEGAL_POLICY_IDS = {
  terms: 'terms',
  privacy: 'privacy',
  cancellationRefunds: 'cancellationRefunds',
  codeOfConduct: 'codeOfConduct',
}

export const LEGAL_POLICIES = {
  [LEGAL_POLICY_IDS.terms]: {
    id: LEGAL_POLICY_IDS.terms,
    eyebrow: 'Legal',
    title: 'Terms of Service',
    summary: 'The basic terms for using Pickup Lane.',
    sections: [
      {
        title: 'Using Pickup Lane',
        body: 'Pickup Lane helps players find, join, host, and manage pickup soccer games. You are responsible for showing up on time, respecting other players, and following venue rules.',
      },
      {
        title: 'Games and payments',
        body: 'Game details, prices, cancellation rules, and host responsibilities may vary by game. Payments, credits, refunds, and deposits will follow the rules shown before checkout or publishing.',
      },
      {
        title: 'Account behavior',
        body: 'We may restrict or remove accounts that abuse the platform, repeatedly no-show, create unsafe games, or violate community expectations.',
      },
      {
        title: 'Placeholder notice',
        body: 'These terms are a working product placeholder while Pickup Lane is in development. Final legal language should be reviewed before launch.',
      },
    ],
  },
  [LEGAL_POLICY_IDS.privacy]: {
    id: LEGAL_POLICY_IDS.privacy,
    eyebrow: 'Privacy',
    title: 'Privacy Policy',
    summary: 'How Pickup Lane handles account and game information.',
    sections: [
      {
        title: 'Information we collect',
        body: 'We collect account details, game activity, profile information, and settings needed to run Pickup Lane. Payment details should be handled by our payment provider, not stored directly by Pickup Lane.',
      },
      {
        title: 'How we use it',
        body: 'We use your information to authenticate your account, show relevant games, manage bookings, send account and game updates, and keep the platform safe.',
      },
      {
        title: 'Account deletion',
        body: 'If you delete your account, we remove your sign-in access and anonymize or delete personal profile details while keeping limited records needed for payments, disputes, security, or game history.',
      },
      {
        title: 'Placeholder notice',
        body: 'This privacy policy is a working product placeholder while Pickup Lane is in development. Final legal language should be reviewed before launch.',
      },
    ],
  },
  [LEGAL_POLICY_IDS.cancellationRefunds]: {
    id: LEGAL_POLICY_IDS.cancellationRefunds,
    eyebrow: 'Policy',
    title: 'Cancellation and Refund Policy',
    summary: 'How cancellations, refunds, credits, waitlists, and weather are handled.',
    sections: [
      {
        title: 'Official games',
        body: 'For official games, Pickup Lane manages checkout, refunds, and game credits. Cancel 24+ hours before game time to be eligible for a refund or game credit. Late cancellations may not be refunded.',
      },
      {
        title: 'If Pickup Lane cancels',
        body: 'If Pickup Lane cancels an official game because of weather, venue issues, or another operational reason, confirmed players receive a refund or game credit.',
      },
      {
        title: 'Community games',
        body: "Community games use the host's posted payment instructions. Pickup Lane does not process player refunds for off-app payments between players and hosts.",
      },
      {
        title: 'Waitlist',
        body: 'Waitlisted players only pay if they are moved to the confirmed player list.',
      },
      {
        title: 'Guests',
        body: "Guest spots follow the same cancellation timing as the player's booking. If a guest is removed before the game, any refund or credit depends on the game type and posted policy.",
      },
      {
        title: 'Weather and safety',
        body: 'Outdoor games may be canceled for dangerous weather, including thunderstorms, lightning, unsafe field conditions, or severe weather.',
      },
      {
        title: 'Development notice',
        body: 'This policy is a working product policy while Pickup Lane is in development. Final legal language should be reviewed before launch.',
      },
    ],
  },
  [LEGAL_POLICY_IDS.codeOfConduct]: {
    id: LEGAL_POLICY_IDS.codeOfConduct,
    eyebrow: 'Conduct',
    title: 'Code of Conduct',
    summary: 'The expectations for players, hosts, and guests using Pickup Lane.',
    sections: [
      {
        title: 'Respect the game',
        body: 'Respect players, hosts, venues, and posted game rules. Come ready to play safely and keep the game organized.',
      },
      {
        title: 'Unsafe behavior',
        body: 'Fighting, threats, harassment, or unsafe play can lead to removal from a game or account restrictions.',
      },
      {
        title: 'Reliability',
        body: 'Repeated no-shows, late cancellations, or misuse of booking and request tools may limit access to Pickup Lane.',
      },
    ],
  },
}

export function getLegalPolicy(policyId) {
  return LEGAL_POLICIES[policyId] || null
}
