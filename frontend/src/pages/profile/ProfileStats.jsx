import { SoccerBallIcon } from '../../components/BrowseIcons.jsx'
import { ClockAlertIcon, NoShowIcon, ShoeIcon } from './ProfileIcons.jsx'

export function ProfileStats({ stats }) {
  const statCards = [
    {
      icon: <SoccerBallIcon />,
      label: 'Games Played',
      meta: 'All time',
      value: stats.games_played_count,
    },
    {
      icon: <ShoeIcon />,
      label: 'Hosted Completed',
      meta: 'All time',
      value: stats.games_hosted_completed_count,
    },
    {
      icon: <NoShowIcon />,
      label: 'No-Shows',
      meta: 'Last 90 days',
      value: stats.no_show_count,
    },
    {
      icon: <ClockAlertIcon />,
      label: 'Late Cancels',
      meta: 'Last 90 days',
      value: stats.late_cancel_count,
    },
  ]

  return (
    <section className="profile-stat-grid" aria-label="Player stats">
      {statCards.map((item) => (
        <article className="profile-stat-card" key={item.label}>
          <span className="profile-stat-card__icon">{item.icon}</span>
          <div>
            <h2>{item.label}</h2>
            <p>{item.meta}</p>
          </div>
          <strong>{item.value}</strong>
        </article>
      ))}
    </section>
  )
}
