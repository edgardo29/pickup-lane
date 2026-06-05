import { useEffect, useRef, useState } from 'react'
import { Share2 as ShareIcon } from 'lucide-react'
import {
  GameEnvironmentIcon,
  GameFormatIcon,
  GamePlayerGroupIcon,
  GameSkillIcon,
  GameTraitIcon,
} from '../../components/GameFactIcons.jsx'
import {
  buildPostHeadline,
  formatSkillLabel,
  formatStatus,
} from './needASubFormatters.js'

export function NeedASubDetailHero({ post }) {
  const [shareCopied, setShareCopied] = useState(false)
  const shareCopiedTimeoutRef = useRef(null)

  useEffect(() => () => {
    if (shareCopiedTimeoutRef.current) {
      window.clearTimeout(shareCopiedTimeoutRef.current)
    }
  }, [])

  function showShareCopied() {
    setShareCopied(true)

    if (shareCopiedTimeoutRef.current) {
      window.clearTimeout(shareCopiedTimeoutRef.current)
    }

    shareCopiedTimeoutRef.current = window.setTimeout(() => {
      setShareCopied(false)
      shareCopiedTimeoutRef.current = null
    }, 1800)
  }

  async function handleSharePost() {
    const shareUrl = `${window.location.origin}/need-a-sub/posts/${post.id}`
    const shareData = {
      title: buildPostHeadline(post),
      text: 'Check out this Need a Sub post on Pickup Lane.',
      url: shareUrl,
    }

    try {
      setShareCopied(false)

      if (navigator.share) {
        await navigator.share(shareData)
        showShareCopied()
        return
      }

      await navigator.clipboard?.writeText(shareUrl)
      showShareCopied()
    } catch (shareError) {
      if (shareError?.name === 'AbortError') {
        return
      }
    }
  }

  return (
    <section className="need-sub-detail-hero" aria-labelledby="need-sub-detail-title">
      <div className="need-sub-detail-hero__header">
        <div className="need-sub-detail-hero__copy">
          <div className="need-sub-detail-hero__title-row">
            <h1 id="need-sub-detail-title">
              <HighlightedPostHeadline post={post} />
            </h1>
          </div>
          <p>Review the game info and request an open substitute spot.</p>
        </div>
        <button className="need-sub-detail-share" type="button" onClick={handleSharePost}>
          <span className="need-sub-detail-share__icon" aria-hidden="true">
            <ShareIcon />
          </span>
          <span>{shareCopied ? 'Copied' : 'Share Post'}</span>
        </button>
      </div>

      <div className="need-sub-detail-game-setup" aria-label="Game setup">
        <span className="need-sub-detail-game-setup__label">
          <GameTraitIcon aria-hidden="true" />
          <span>Game Setup</span>
        </span>
        <div className="need-sub-detail-game-setup__facts">
          <GameSetupFact icon={<GamePlayerGroupIcon />} label="Player group">
            {formatStatus(post.game_player_group)}
          </GameSetupFact>
          <GameSetupFact icon={<GameFormatIcon />} label="Format">
            {post.format_label || 'Format not listed'}
          </GameSetupFact>
          <GameSetupFact icon={<GameSkillIcon />} label="Skill level">
            {formatSkillLabel(post.skill_level)}
          </GameSetupFact>
          <GameSetupFact icon={<GameEnvironmentIcon />} label="Environment">
            {post.environment_type ? formatStatus(post.environment_type) : 'Environment not listed'}
          </GameSetupFact>
        </div>
      </div>
    </section>
  )
}

function GameSetupFact({ children, icon, label }) {
  return (
    <div className="need-sub-detail-game-setup__fact">
      <span aria-hidden="true">{icon}</span>
      <div>
        <small>{label}</small>
        <strong>{children}</strong>
      </div>
    </div>
  )
}

function HighlightedPostHeadline({ post }) {
  const headline = buildPostHeadline(post)
  const count = String(post.subs_needed)
  const [beforeCount, afterCount = ''] = headline.split(count)

  return (
    <>
      {beforeCount}<span>{count}</span>{afterCount}
    </>
  )
}
