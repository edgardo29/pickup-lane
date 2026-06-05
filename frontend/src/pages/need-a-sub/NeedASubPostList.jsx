import { Link } from 'react-router-dom'
import {
  BuildingIcon,
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import {
  NeedSubFieldPlayersIcon,
  NeedSubGoalkeeperIcon,
} from '../../components/GameFactIcons.jsx'
import {
  buildPostSubtitle,
  formatDateWithYear,
  formatStatus,
  formatTimeRangeOnly,
} from './needASubFormatters.js'
import { NeedASubPostListSkeleton } from './NeedASubSkeleton.jsx'

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
        <NeedASubPostListSkeleton />
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
  const needGroups = buildNeedGroups(post)
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
        <span className="need-sub-post__needs-title">Open Spots</span>
        {needGroups.map((group) => {
          const GroupIcon = group.icon

          return (
            <div className="need-sub-post__needs-group" key={group.key}>
              <div className="need-sub-post__need-summary">
                <GroupIcon />
                <h4>{group.label}</h4>
                <strong>{formatOpenCount(group.spotsLeft)}</strong>
              </div>
              <p title={formatPlayerLabels(group.rows)}>{formatPlayerLabels(group.rows)}</p>
            </div>
          )
        })}
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

const NEED_GROUP_ORDER = [
  { key: 'field_player', label: 'Field Players', icon: NeedSubFieldPlayersIcon },
  { key: 'goalkeeper', label: 'Goalkeepers', icon: NeedSubGoalkeeperIcon },
]

const PLAYER_GROUP_ORDER = [
  { key: 'open', label: 'Any' },
  { key: 'men', label: 'Men' },
  { key: 'women', label: 'Women' },
]

function buildNeedGroups(post) {
  const positions = post.positions?.length
    ? post.positions
    : [{
        player_group: 'open',
        position_label: 'field_player',
        spots_needed: Math.max(0, Number(post.subs_needed || 0) - Number(post.confirmed_count || 0)),
      }]

  return NEED_GROUP_ORDER.map((group) => {
    const positionsForGroup = positions.filter((position) => position.position_label === group.key)
    const rows = PLAYER_GROUP_ORDER.flatMap((playerGroup) => {
      const matchingPositions = positionsForGroup.filter(
        (position) => position.player_group === playerGroup.key,
      )

      if (!matchingPositions.length) {
        return []
      }

      const spotsLeft = positionsForGroup.reduce((sum, position) => {
        if (position.player_group !== playerGroup.key) {
          return sum
        }

        return sum + Math.max(
          0,
          Number(position.spots_needed || 0) - Number(position.confirmed_count || 0),
        )
      }, 0)

      return [{
        key: `${group.key}:${playerGroup.key}`,
        label: playerGroup.label,
        spotsLeft,
      }]
    })

    return {
      ...group,
      spotsLeft: rows.reduce((sum, row) => sum + row.spotsLeft, 0),
      rows,
    }
  })
    .filter((group) => group.rows.length > 0)
}

function formatOpenCount(spotsLeft) {
  return `${spotsLeft} open`
}

function formatPlayerLabels(rows) {
  return rows.map((row) => row.label).join(' · ')
}

function Fact({ icon, text }) {
  return (
    <span>
      {icon}
      <span className="need-sub-post__fact-text" title={text}>{text}</span>
    </span>
  )
}

export default NeedASubPostList
