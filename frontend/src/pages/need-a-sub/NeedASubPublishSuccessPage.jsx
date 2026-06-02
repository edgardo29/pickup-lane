import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { AppPageShell } from '../../components/app/index.js'
import {
  AddressIcon,
  GameDateIcon,
  GameSpotsIcon,
  GameStatusIcon,
  GameTimeIcon,
} from '../../components/GameFactIcons.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import { getNeedASubPost } from './needASubApi.js'
import {
  buildPostHeadline,
  buildPostSubtitle,
  formatDateWithYear,
  formatLocation,
  formatTimeRangeOnly,
} from './needASubFormatters.js'
import '../../styles/need-a-sub/NeedASub.css'

function NeedASubPublishSuccessPage() {
  const { postId } = useParams()
  const { state } = useLocation()
  const { currentUser, isLoading: isAuthLoading } = useAuth()
  const routedPost = state?.post || null
  const [post, setPost] = useState(routedPost)
  const [isLoading, setIsLoading] = useState(!routedPost)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isAuthLoading || !postId || post?.id === postId) {
      return undefined
    }

    let isMounted = true

    async function loadPost() {
      setIsLoading(true)
      setError('')

      try {
        const response = await getNeedASubPost(postId, currentUser)

        if (isMounted) {
          setPost(response)
        }
      } catch (loadError) {
        if (isMounted) {
          setError(loadError instanceof Error ? loadError.message : 'Unable to load the published post.')
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    loadPost()

    return () => {
      isMounted = false
    }
  }, [currentUser, isAuthLoading, post?.id, postId])

  return (
    <AppPageShell className="need-sub-page" mainClassName="need-sub-shell need-sub-success-shell">
      <section className="need-sub-publish-success" aria-labelledby="need-sub-publish-success-title">
        <div className="need-sub-publish-success__mark" aria-hidden="true">
          <GameStatusIcon />
        </div>

        <div className="need-sub-publish-success__copy">
          <span>Post published</span>
          <h1 id="need-sub-publish-success-title">Sub post published</h1>
          <p>Your sub post is live. Players can now request the spot.</p>
        </div>

        {error && (
          <div className="need-sub-alert need-sub-alert--error need-sub-publish-success__alert">
            {error}
          </div>
        )}

        {isLoading && !post ? (
          <div className="need-sub-publish-success__summary">
            <strong>Loading post...</strong>
          </div>
        ) : post ? (
          <SuccessSummary post={post} />
        ) : null}

        <div className="need-sub-publish-success__actions">
          <Link className="need-sub-primary" to={`/need-a-sub/posts/${postId}`}>
            View Post
            <span aria-hidden="true">→</span>
          </Link>
          <Link className="need-sub-create-secondary" to="/need-a-sub">
            Back to Need a Sub
          </Link>
        </div>
      </section>
    </AppPageShell>
  )
}

function SuccessSummary({ post }) {
  return (
    <div className="need-sub-publish-success__summary">
      <div className="need-sub-publish-success__summary-heading">
        <strong>{buildPostHeadline(post)}</strong>
        <span>{buildPostSubtitle(post)}</span>
      </div>

      <div className="need-sub-publish-success__facts">
        <SuccessFact icon={<GameDateIcon />} label={formatDateWithYear(post.starts_at)} />
        <SuccessFact icon={<GameTimeIcon />} label={formatTimeRangeOnly(post)} />
        <SuccessFact icon={<AddressIcon />} label={formatLocation(post, { includeStreet: true })} />
        <SuccessFact
          icon={<GameSpotsIcon />}
          label={`${post.confirmed_count || 0}/${post.subs_needed} spots filled`}
        />
      </div>
    </div>
  )
}

function SuccessFact({ icon, label }) {
  return (
    <span className="need-sub-publish-success__fact">
      {icon}
      <span>{label}</span>
    </span>
  )
}

export default NeedASubPublishSuccessPage
