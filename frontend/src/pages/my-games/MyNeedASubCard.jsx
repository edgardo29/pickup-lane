import { Link } from 'react-router-dom'
import {
  BuildingIcon,
  MapPinIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import {
  GameTimeIcon,
  GameTraitIcon,
  NeedSubFieldPlayersIcon,
  NeedSubGoalkeeperIcon,
} from '../../components/GameFactIcons.jsx'
import {
  formatEnvironment,
  formatGamePlayerGroup,
  formatTimeRange,
} from './myGamesFormatters.js'

function MyNeedASubCard({ item }) {
  const { post } = item
  const canViewDetail = Boolean(item.canViewDetail ?? item.can_view_detail)
  const statusTone = item.statusTone || item.status_tone
  const statusBadge = getVisibleStatusBadge(statusTone)
  const locationLabel = [post.city, post.state].filter(Boolean).join(', ')
  const postSpec = [
    formatGamePlayerGroup(post.game_player_group),
    post.format_label,
    formatEnvironment(post.environment_type),
  ].filter(Boolean).join(' · ')
  const needGroups = buildNeedGroups(post)
  const confirmedCount = post.confirmed_count || 0

  const CardElement = canViewDetail ? Link : 'article'
  const cardProps = canViewDetail
    ? { to: `/need-a-sub/posts/${post.id}` }
    : { 'aria-disabled': 'true' }

  return (
    <CardElement
      className={`my-need-sub-card app-hover-card ${
        canViewDetail ? '' : 'my-need-sub-card--disabled'
      } my-game-card--${statusTone}`}
      {...cardProps}
    >
      <div className="my-need-sub-card__top">
        <div className="my-need-sub-card__title-row">
          <strong>
            Need <span>{post.subs_needed}</span> {post.subs_needed === 1 ? 'Sub' : 'Subs'}
          </strong>
          {statusBadge && (
            <span className={`my-game-card__status my-game-card__status--${statusTone}`}>
              {statusBadge}
            </span>
          )}
        </div>
      </div>

      <div className="my-need-sub-card__facts">
        <Fact icon={<BuildingIcon />} text={post.location_name || 'Pickup Lane'} />
        <Fact icon={<MapPinIcon />} text={locationLabel || 'Location not set'} />
        <Fact icon={<GameTimeIcon />} text={formatTimeRange(post.starts_at, post.ends_at)} />
        <Fact icon={<GameTraitIcon />} text={postSpec} />
      </div>

      <div className="my-need-sub-card__needs">
        <span className="my-need-sub-card__needs-title">Open Spots</span>
        {needGroups.map((group) => {
          const GroupIcon = group.icon

          return (
            <div className="my-need-sub-card__needs-group" key={group.key}>
              <div className="my-need-sub-card__need-summary">
                <GroupIcon />
                <h4>{group.label}</h4>
                <strong>{formatOpenCount(group.spotsLeft)}</strong>
              </div>
              <p title={formatPlayerLabels(group.rows)}>{formatPlayerLabels(group.rows)}</p>
            </div>
          )
        })}
      </div>

      <div className="my-need-sub-card__footer">
        <span>
          <UsersIcon />
          {confirmedCount}/{post.subs_needed} spots
        </span>
        {canViewDetail && <span className="my-need-sub-card__arrow" aria-hidden="true">›</span>}
      </div>
    </CardElement>
  )
}

function Fact({ icon, text }) {
  return (
    <span>
      {icon}
      <span className="my-need-sub-card__fact-text">{text}</span>
    </span>
  )
}

function getVisibleStatusBadge(statusTone) {
  if (statusTone === 'cancelled') {
    return 'Cancelled'
  }

  if (statusTone === 'owner') {
    return 'Owner'
  }

  return ''
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
        spots_needed: Math.max(
          0,
          Number(post.subs_needed || 0) - Number(post.confirmed_count || 0),
        ),
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
  }).filter((group) => group.rows.length > 0)
}

function formatOpenCount(spotsLeft) {
  return `${spotsLeft} open`
}

function formatPlayerLabels(rows) {
  return rows.map((row) => row.label).join(' · ')
}

export default MyNeedASubCard
