import { Link } from 'react-router-dom'
import {
  BuildingIcon,
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import {
  buildPostSubtitle,
  formatDateWithYear,
  formatStatus,
  formatTimeRangeOnly,
} from './needASubFormatters.js'
import { countHeldSpots } from './needASubSelectors.js'

function NeedASubPostList({
  isLoading,
  isSignedIn,
  onOpenPost,
  postView,
  posts,
}) {
  return (
    <section className="need-sub-panel">
      {postView === 'mine' && !isSignedIn ? (
        <NeedASubState
          title="Sign in to manage posts"
          message="Your created posts and request queues live behind your account."
          action={<Link to="/sign-in" state={{ from: '/need-a-sub' }}>Sign In</Link>}
        />
      ) : isLoading ? (
        <NeedASubState title="Loading Need a Sub posts" />
      ) : !posts.length ? (
        <NeedASubState
          title={postView === 'mine' ? 'No posts created yet' : 'No Need a Sub posts yet'}
          message={postView === 'mine' ? 'Create one when your team needs players.' : 'Check back soon or create your own post.'}
        />
      ) : (
        <div className="need-sub-post-grid">
          {posts.map((post) => (
            <NeedASubPostCard
              key={post.id}
              post={post}
              onOpenPost={onOpenPost}
            />
          ))}
        </div>
      )}
    </section>
  )
}

function NeedASubPostCard({ onOpenPost, post }) {
  const playerTypeSummaries = buildPlayerTypeSummaries(post).filter(
    (summary) => summary.spotsLeft > 0,
  )
  const cityState = [post.city, post.state].filter(Boolean).join(', ')
  const environmentLabel = post.environment_type ? formatStatus(post.environment_type) : ''

  return (
    <article
      className="need-sub-post"
      role="button"
      tabIndex={0}
      onClick={() => onOpenPost(post)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onOpenPost(post)
        }
      }}
    >
      <div className="need-sub-post__top">
        <div className="need-sub-post__title-row">
          <strong>
            Need <span>{post.subs_needed}</span> {post.subs_needed === 1 ? 'Sub' : 'Subs'}
          </strong>
          {environmentLabel && (
            <span className="need-sub-post__environment">{environmentLabel}</span>
          )}
        </div>
        <small>{buildPostSubtitle(post)}</small>
      </div>

      <div className="need-sub-post__facts">
        <Fact icon={<BuildingIcon />} text={post.location_name || 'Pickup Lane'} />
        <Fact icon={<MapPinIcon />} text={cityState || 'Location not set'} />
        <Fact icon={<CalendarIcon />} text={formatDateWithYear(post.starts_at)} />
        <Fact icon={<ClockIcon />} text={formatTimeRangeOnly(post)} />
      </div>

      <div className="need-sub-post__needs">
        {playerTypeSummaries.map((summary) => (
          <span
            className="need-sub-post__need-row"
            key={summary.key}
          >
            <small>{summary.label}</small>
            <strong>{formatOpenCount(summary.spotsLeft)}</strong>
          </span>
        ))}
      </div>

      <div className="need-sub-post__footer">
        <span>
          <UsersIcon />
          {post.confirmed_count || 0}/{post.subs_needed} spots
        </span>
        <span className="need-sub-card-arrow" aria-hidden="true">›</span>
      </div>
    </article>
  )
}

export function NeedASubState({ action = null, message = '', title }) {
  return (
    <div className="need-sub-state">
      <MapPinIcon />
      <h2>{title}</h2>
      {message && <p>{message}</p>}
      {action && <div className="need-sub-state__action">{action}</div>}
    </div>
  )
}

const PLAYER_TYPE_SUMMARY_ORDER = [
  { key: 'men', label: 'Men' },
  { key: 'women', label: 'Women' },
  { key: 'open', label: 'Any Player' },
]

function buildPlayerTypeSummaries(post) {
  const spotsByGroup = new Map(PLAYER_TYPE_SUMMARY_ORDER.map((group) => [group.key, 0]))

  ;(post.positions || []).forEach((position) => {
    const spotsLeft = Math.max(0, Number(position.spots_needed || 0) - countHeldSpots(position))
    spotsByGroup.set(position.player_group, (spotsByGroup.get(position.player_group) || 0) + spotsLeft)
  })

  return PLAYER_TYPE_SUMMARY_ORDER.map((group) => ({
    ...group,
    spotsLeft: spotsByGroup.get(group.key) || 0,
  }))
}

function formatOpenCount(spotsLeft) {
  return `${spotsLeft} open`
}

function Fact({ icon, text }) {
  return (
    <span>
      {icon}
      {text}
    </span>
  )
}

export default NeedASubPostList
