import { HostRulesIcon } from '../../components/GameFactIcons.jsx'
import { NeedASubDetailSectionHeading } from './NeedASubDetailSectionHeading.jsx'

const nextStepsByRole = {
  owner: [
    {
      title: 'Review requests',
      text: 'Accept or decline players from Manage Requests.',
    },
    {
      title: 'Keep details accurate',
      text: 'Update the post if anything changes before game time.',
    },
    {
      title: 'Be ready to play',
      text: "Once your subs are set, you're covered for game day.",
    },
  ],
  requester: [
    {
      title: 'Request a spot',
      text: 'Choose a spot type and submit your request.',
    },
    {
      title: 'Host reviews',
      text: 'The host will review your request.',
    },
    {
      title: 'Get notified',
      text: "You'll get an Inbox update if your request is approved.",
    },
  ],
}

export function NeedASubNextSteps({ role = 'requester' }) {
  const nextSteps = nextStepsByRole[role] || nextStepsByRole.requester

  return (
    <section className="need-sub-detail-section need-sub-next-steps">
      <NeedASubDetailSectionHeading eyebrow="What Happens Next?" icon={<HostRulesIcon />} />
      <div className="need-sub-next-steps__grid">
        {nextSteps.map((step, index) => (
          <div className="need-sub-next-step" key={step.title}>
            <span>{index + 1}</span>
            <div>
              <strong>{step.title}</strong>
              <p>{step.text}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
