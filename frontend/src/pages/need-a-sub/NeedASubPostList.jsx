import { Link } from 'react-router-dom'
import {
  BuildingIcon,
  ClockIcon,
  MapPinIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import {
  GameTraitIcon,
  NeedSubFieldPlayersIcon,
  NeedSubGoalkeeperIcon,
} from '../../components/GameFactIcons.jsx'
import {
  formatStatus,
  formatTimeRangeOnly,
} from './needASubFormatters.js'
import { NeedASubPostListSkeleton } from './NeedASubSkeleton.jsx'

function NeedASubPostList({
  hasMorePosts = false,
  isLoading,
  isLoadingMore = false,
  isSignedIn,
  onLoadMore,
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
        <>
          <div className="need-sub-results">
            {groupPostsByHour(posts).map((group) => (
              <NeedASubTimeSection
                group={group}
                key={group.label}
                onOpenPost={onOpenPost}
              />
            ))}
          </div>

          {hasMorePosts && (
            <div className="need-sub-load-more">
              <button
                type="button"
                onClick={onLoadMore}
                disabled={isLoadingMore}
              >
                {isLoadingMore ? 'Loading...' : 'Load More'}
              </button>
            </div>
          )}
        </>
      )}
    </section>
  )
}

function NeedASubTimeSection({ group, onOpenPost }) {
  return (
    <section className="need-sub-time-section">
      <div className="need-sub-time-section__header">
        <h2>
          <ClockIcon />
          {group.label}
        </h2>
        <span className="need-sub-time-section__count">
          {group.posts.length} {group.posts.length === 1 ? 'post' : 'posts'}
        </span>
      </div>

      <div className="need-sub-post-grid">
        {group.posts.map((post) => (
          <NeedASubPostCard
            key={post.id}
            post={post}
            onOpenPost={onOpenPost}
          />
        ))}
      </div>
    </section>
  )
}

function NeedASubPostCard({ onOpenPost, post }) {
  const needGroups = buildNeedGroups(post)
  const cityState = [post.city, post.state].filter(Boolean).join(', ')
  const environmentLabel = post.environment_type ? formatStatus(post.environment_type) : ''
  const postSpec = [
    formatStatus(post.game_player_group),
    post.format_label,
    environmentLabel,
  ].filter(Boolean).join(' · ')

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
        </div>
      </div>

      <div className="need-sub-post__facts">
        <Fact icon={<BuildingIcon />} text={post.location_name || 'Pickup Lane'} />
        <Fact icon={<MapPinIcon />} text={cityState || 'Location not set'} />
        <Fact icon={<ClockIcon />} text={formatTimeRangeOnly(post)} />
        <Fact icon={<GameTraitIcon />} text={postSpec} />
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

function groupPostsByHour(posts) {
  const groupedPosts = [...posts]
    .sort((first, second) => new Date(first.starts_at) - new Date(second.starts_at))
    .reduce((groups, post) => {
      const date = new Date(post.starts_at)
      const label = new Intl.DateTimeFormat('en-US', { hour: 'numeric' }).format(date)

      if (!groups.has(label)) {
        groups.set(label, [])
      }

      groups.get(label).push(post)
      return groups
    }, new Map())

  return [...groupedPosts.entries()].map(([label, groupPosts]) => ({
    label,
    posts: groupPosts,
  }))
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
