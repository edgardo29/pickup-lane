import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import BrowseAppNav from '../components/BrowseAppNav.jsx'
import {
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
} from '../components/BrowseIcons.jsx'
import { useAuth } from '../hooks/useAuth.js'
import {
  createNeedASubPost,
  listMyNeedASubRequests,
  listNeedASubPosts,
} from '../lib/needASubApi.js'
import '../styles/browse-games.css'
import '../styles/need-a-sub.css'

const formatOptions = ['5v5', '6v6', '7v7', '8v8', '9v9', '10v10', '11v11']
const skillOptions = [
  { label: 'Any', value: 'any' },
  { label: 'Beginner', value: 'beginner' },
  { label: 'Recreational', value: 'recreational' },
  { label: 'Intermediate', value: 'intermediate' },
  { label: 'Advanced', value: 'advanced' },
  { label: 'Competitive', value: 'competitive' },
]
const groupOptions = [
  { label: 'Open', value: 'open' },
  { label: 'Men', value: 'men' },
  { label: 'Women', value: 'women' },
  { label: 'Coed', value: 'coed' },
]
const positionOptions = [
  { label: 'Field Player', value: 'field_player' },
  { label: 'Goalkeeper', value: 'goalkeeper' },
]
const maxSubRows = 6
const maxTotalSubs = 11
const dateOptions = buildDateOptions()
const timeOptions = buildTimeOptions()

const initialForm = {
  date: getDefaultDate(),
  startTime: '19:00',
  endTime: '21:00',
  formatLabel: '7v7',
  skillLevel: 'intermediate',
  gamePlayerGroup: 'coed',
  locationName: '',
  addressLine1: '',
  city: 'Chicago',
  state: 'IL',
  postalCode: '',
  neighborhood: '',
  priceDue: 0,
  notes: '',
  positions: getDefaultPositions('coed'),
}

function NeedASubPage() {
  const { appUser, currentUser } = useAuth()
  const navigate = useNavigate()
  const [posts, setPosts] = useState([])
  const [myRequests, setMyRequests] = useState([])
  const [form, setForm] = useState(initialForm)
  const [isCreating, setIsCreating] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')
  const [activePanel, setActivePanel] = useState('browse')
  const [postView, setPostView] = useState('all')

  const refreshNeedASub = useCallback(async ({ showLoading = false } = {}) => {
    if (showLoading) {
      setIsLoading(true)
    }
    setError('')

    try {
      const [postsResponse, requestResponse] = await Promise.all([
        listNeedASubPosts(),
        currentUser ? listMyNeedASubRequests(currentUser).catch(() => []) : Promise.resolve([]),
      ])

      setPosts(postsResponse)
      setMyRequests(requestResponse)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load Need a Sub.')
    } finally {
      if (showLoading) {
        setIsLoading(false)
      }
    }
  }, [currentUser])

  useEffect(() => {
    let ignore = false

    async function loadInitialNeedASub() {
      setIsLoading(true)
      setError('')

      try {
        const [postsResponse, requestResponse] = await Promise.all([
          listNeedASubPosts(),
          currentUser ? listMyNeedASubRequests(currentUser).catch(() => []) : Promise.resolve([]),
        ])

        if (!ignore) {
          setPosts(postsResponse)
          setMyRequests(requestResponse)
        }
      } catch (loadError) {
        if (!ignore) {
          setError(loadError instanceof Error ? loadError.message : 'Unable to load Need a Sub.')
        }
      } finally {
        if (!ignore) {
          setIsLoading(false)
        }
      }
    }

    loadInitialNeedASub()

    return () => {
      ignore = true
    }
  }, [currentUser])

  useEffect(() => {
    function refreshVisibleNeedASub() {
      if (document.visibilityState === 'visible') {
        refreshNeedASub()
      }
    }

    window.addEventListener('focus', refreshNeedASub)
    document.addEventListener('visibilitychange', refreshVisibleNeedASub)

    return () => {
      window.removeEventListener('focus', refreshNeedASub)
      document.removeEventListener('visibilitychange', refreshVisibleNeedASub)
    }
  }, [refreshNeedASub])

  const visiblePosts = useMemo(
    () =>
      postView === 'mine'
        ? posts.filter((post) => post.owner_user_id === appUser?.id)
        : posts,
    [appUser?.id, postView, posts],
  )
  const totalSpotsNeeded = useMemo(
    () => form.positions.reduce((sum, position) => sum + Number(position.spots_needed || 0), 0),
    [form.positions],
  )

  function updateField(field, value) {
    setNotice('')
    setError('')
    setFormError('')
    setForm((currentForm) => ({ ...currentForm, [field]: value }))
  }

  function updateGamePlayerGroup(value) {
    setNotice('')
    setError('')
    setFormError('')
    setForm((currentForm) => ({
      ...currentForm,
      gamePlayerGroup: value,
      positions: getDefaultPositions(value),
    }))
  }

  function updatePosition(index, field, value) {
    setNotice('')
    setError('')
    setFormError('')
    setForm((currentForm) => ({
      ...currentForm,
      positions: currentForm.positions.map((position, currentIndex) =>
        currentIndex === index
          ? { ...position, [field]: field === 'spots_needed' ? Number(value) : value }
          : position,
      ),
    }))
  }

  function addPosition() {
    setForm((currentForm) => ({
      ...currentForm,
      positions: [
        ...currentForm.positions,
        {
          ...getNextPosition(currentForm.positions, currentForm.gamePlayerGroup),
          spots_needed: 1,
          sort_order: currentForm.positions.length,
        },
      ],
    }))
  }

  function removePosition(index) {
    setForm((currentForm) => ({
      ...currentForm,
      positions: currentForm.positions
        .filter((_, currentIndex) => currentIndex !== index)
        .map((position, sortOrder) => ({ ...position, sort_order: sortOrder })),
    }))
  }

  async function submitPost(event) {
    event.preventDefault()

    const validationError = validateForm(form)
    if (validationError) {
      setFormError(validationError)
      return
    }

    setIsCreating(true)
    setError('')
    setNotice('')

    try {
      const payload = buildCreatePayload(form, totalSpotsNeeded)
      await createNeedASubPost(currentUser, payload)
      setPostView('mine')
      setForm(initialForm)
      setActivePanel('browse')
      await refreshNeedASub({ showLoading: true })
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to create post.')
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <div className="need-sub-page">
      <BrowseAppNav />

      <main className="need-sub-shell">
        <section className="need-sub-hero">
          <div>
            <p>Need a Sub</p>
            <h1>Find subs for games outside Pickup Lane.</h1>
            <span>
              Create structured sub posts, review requests, and keep confirmed players organized.
            </span>
          </div>
          <div className="need-sub-hero__actions">
            <button
              className={activePanel === 'browse' ? 'active' : ''}
              type="button"
              onClick={() => setActivePanel('browse')}
            >
              Browse Posts
            </button>
            <button
              className={activePanel === 'create' ? 'active' : ''}
              type="button"
              onClick={() => setActivePanel('create')}
            >
              Create Post
            </button>
          </div>
        </section>

        {(notice || error) && (
          <div className={`need-sub-alert ${error ? 'need-sub-alert--error' : ''}`}>
            {error || notice}
          </div>
        )}

        <div className={`need-sub-layout ${activePanel === 'create' ? 'need-sub-layout--create' : ''}`}>
          <section className="need-sub-main">
            {activePanel === 'create' ? (
              <CreateNeedASubForm
                formError={formError}
                form={form}
                isCreating={isCreating}
                totalSpotsNeeded={totalSpotsNeeded}
                onAddPosition={addPosition}
                onRemovePosition={removePosition}
                onSubmit={submitPost}
                onUpdateField={updateField}
                onUpdateGamePlayerGroup={updateGamePlayerGroup}
                onUpdatePosition={updatePosition}
              />
            ) : (
              <NeedASubPostList
                appUser={appUser}
                isLoading={isLoading}
                myRequests={myRequests}
                onOpenPost={(post) => navigate(`/need-a-sub/posts/${post.id}`)}
                onRefresh={() => refreshNeedASub({ showLoading: true })}
                posts={visiblePosts}
                postView={postView}
                setPostView={setPostView}
              />
            )}
          </section>
        </div>
      </main>
    </div>
  )
}

function CreateNeedASubForm({
  form,
  formError,
  isCreating,
  onAddPosition,
  onRemovePosition,
  onSubmit,
  onUpdateField,
  onUpdateGamePlayerGroup,
  onUpdatePosition,
  submitLabel = 'Publish Post',
  totalSpotsNeeded,
}) {
  const playerGroupOptions = getPositionGroupOptions(form.gamePlayerGroup)
  const canAddSub = form.positions.length < maxSubRows && totalSpotsNeeded < maxTotalSubs

  return (
    <form className="need-sub-form" onSubmit={onSubmit}>
      <div className="need-sub-form-title">
        <p>Create post</p>
        <h2>Game Details</h2>
      </div>

      <section className="need-sub-form-section">
        <div className="need-sub-form-grid need-sub-form-grid--three">
          <Field label="Date">
            <select value={form.date} onChange={(event) => onUpdateField('date', event.target.value)}>
              {dateOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </Field>
          <Field label="Start time">
            <select
              value={form.startTime}
              onChange={(event) => onUpdateField('startTime', event.target.value)}
            >
              {timeOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </Field>
          <Field label="End time">
            <select
              value={form.endTime}
              onChange={(event) => onUpdateField('endTime', event.target.value)}
            >
              {timeOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </Field>
        </div>

        <div className="need-sub-form-grid need-sub-form-grid--three">
          <Field label="Format">
            <select
              value={form.formatLabel}
              onChange={(event) => onUpdateField('formatLabel', event.target.value)}
            >
              {formatOptions.map((format) => (
                <option key={format} value={format}>{format}</option>
              ))}
            </select>
          </Field>
          <Field label="Skill level">
            <select
              value={form.skillLevel}
              onChange={(event) => onUpdateField('skillLevel', event.target.value)}
            >
              {skillOptions.map((skill) => (
                <option key={skill.value} value={skill.value}>{skill.label}</option>
              ))}
            </select>
          </Field>
          <Field label="Player group">
            <select
              value={form.gamePlayerGroup}
              onChange={(event) => onUpdateGamePlayerGroup(event.target.value)}
            >
              {groupOptions.map((group) => (
                <option key={group.value} value={group.value}>{group.label}</option>
              ))}
            </select>
          </Field>
        </div>

      </section>

      <section className="need-sub-form-section">
        <div className="need-sub-card-heading need-sub-card-heading--split">
          <div>
            <p>Sub Requirements <span>(limit {maxTotalSubs})</span></p>
            <small>{totalSpotsNeeded} {totalSpotsNeeded === 1 ? 'Sub' : 'Subs'} currently added</small>
          </div>
          <button disabled={!canAddSub} type="button" onClick={onAddPosition}>+ Add Sub</button>
        </div>

        <div className="need-sub-position-list">
          {form.positions.map((position, index) => (
            <div className="need-sub-position-card" key={`${position.sort_order}-${index}`}>
              <div className="need-sub-position-card__header">
                <span>Sub {index + 1}</span>
                <button
                  className="need-sub-row-remove"
                  disabled={form.positions.length === 1}
                  type="button"
                  onClick={() => onRemovePosition(index)}
                >
                  Remove
                </button>
              </div>
              <div className="need-sub-position-card__fields">
                <Field label="Position">
                  <select
                    value={position.position_label}
                    onChange={(event) => onUpdatePosition(index, 'position_label', event.target.value)}
                  >
                    {positionOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Group">
                  <select
                    value={position.player_group}
                    onChange={(event) => onUpdatePosition(index, 'player_group', event.target.value)}
                  >
                    {playerGroupOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Spots">
                  <input
                    min="1"
                    type="number"
                    value={position.spots_needed}
                    onChange={(event) => onUpdatePosition(index, 'spots_needed', event.target.value)}
                  />
                </Field>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="need-sub-form-section">
        <div className="need-sub-card-heading">
          <p>Location</p>
        </div>

        <div className="need-sub-form-grid need-sub-form-grid--two">
          <Field label="Venue or park name">
            <input
              placeholder="e.g. Rauner YMCA"
              value={form.locationName}
              onChange={(event) => onUpdateField('locationName', event.target.value)}
            />
          </Field>
          <Field label="Street address">
            <input
              placeholder="e.g. 123 Field Ave"
              value={form.addressLine1}
              onChange={(event) => onUpdateField('addressLine1', event.target.value)}
            />
          </Field>
        </div>

        <div className="need-sub-form-grid need-sub-form-grid--four">
          <Field label="City">
            <input value={form.city} onChange={(event) => onUpdateField('city', event.target.value)} />
          </Field>
          <Field label="State">
            <input value={form.state} onChange={(event) => onUpdateField('state', event.target.value)} />
          </Field>
          <Field label="ZIP">
            <input
              value={form.postalCode}
              onChange={(event) => onUpdateField('postalCode', event.target.value)}
            />
          </Field>
          <Field label="Neighborhood (optional)">
            <input
              placeholder="e.g. Pilsen"
              value={form.neighborhood}
              onChange={(event) => onUpdateField('neighborhood', event.target.value)}
            />
          </Field>
        </div>
      </section>

      <section className="need-sub-form-section">
        <div className="need-sub-card-heading">
          <p>Additional Info</p>
        </div>

        <div className="need-sub-price-field">
          <Field label="Price due at venue">
            <input
              min="0"
              type="number"
              value={form.priceDue}
              onChange={(event) => onUpdateField('priceDue', event.target.value)}
            />
          </Field>
        </div>

        <label className="need-sub-textarea">
          <span>Notes (optional)</span>
          <textarea
            maxLength={220}
            placeholder="e.g. Bring a dark shirt. Ask for Luis at the south entrance."
            value={form.notes}
            onChange={(event) => onUpdateField('notes', event.target.value)}
          />
          <small>{form.notes.length}/220</small>
        </label>
      </section>

      <div className="need-sub-form-actions">
        {formError && <div className="need-sub-form-error">{formError}</div>}
        <button className="need-sub-primary" disabled={isCreating} type="submit">
          {isCreating ? 'Saving...' : submitLabel}
        </button>
      </div>
    </form>
  )
}

function NeedASubPostList({
  appUser,
  isLoading,
  myRequests,
  onOpenPost,
  onRefresh,
  postView,
  posts,
  setPostView,
}) {
  function switchPostView(nextView) {
    setPostView(nextView)
    onRefresh()
  }

  return (
    <>
      <div className="need-sub-list-toolbar">
        <div>
          <p>{postView === 'mine' ? 'Manage your posts' : 'All posts'}</p>
          <span>
            {postView === 'mine'
              ? 'Review requests and manage posts you created.'
              : 'Choose a post to request a spot, or manage one you created.'}
          </span>
        </div>
        <div className="need-sub-list-toggle">
          <button
            className={postView === 'all' ? 'active' : ''}
            type="button"
            onClick={() => switchPostView('all')}
          >
            All Posts
          </button>
          <button
            className={postView === 'mine' ? 'active' : ''}
            type="button"
            onClick={() => switchPostView('mine')}
          >
            My Posts
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="need-sub-empty">Loading Need a Sub posts...</div>
      ) : !posts.length ? (
        <div className="need-sub-empty">
          <strong>{postView === 'mine' ? 'You have not created any Need a Sub posts.' : 'No Need a Sub posts yet.'}</strong>
          <span>{postView === 'mine' ? 'Create one when your team needs players.' : 'Check back soon or create your own post.'}</span>
        </div>
      ) : (
        <div className="need-sub-post-list">
          {posts.map((post) => {
            const existingRequest = myRequests.find((request) => request.sub_post_id === post.id)
            const isOwner = appUser?.id === post.owner_user_id
            const isFilled = post.post_status === 'filled'
            const spotsLeft = getSpotsLeft(post)

            return (
              <article
                className="need-sub-post"
                key={post.id}
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
                  <strong>{buildPostHeadline(post)}</strong>
                  <span>{isFilled ? 'Filled' : `${spotsLeft} ${spotsLeft === 1 ? 'spot' : 'spots'} left`}</span>
                </div>
                <div className="need-sub-post__facts">
                  <Fact icon={<CalendarIcon />} text={formatDate(post.starts_at)} />
                  <Fact icon={<ClockIcon />} text={formatTimeRange(post)} />
                  <Fact icon={<MapPinIcon />} text={`${post.location_name} · ${post.city}, ${post.state}`} />
                </div>
                <div className="need-sub-post__footer">
                  {isOwner ? (
                    <span>{getOwnerPostStatus(post)}</span>
                  ) : existingRequest ? (
                    <span>{formatStatus(existingRequest.request_status)}</span>
                  ) : isFilled ? (
                    <span>Filled</span>
                  ) : (
                    <span>View details</span>
                  )}
                  <span className="need-sub-card-arrow" aria-hidden="true">{'->'}</span>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </>
  )
}

function Field({ children, label }) {
  return (
    <label className="need-sub-field">
      <span>{label}</span>
      {children}
    </label>
  )
}

function Fact({ icon, text }) {
  return (
    <span>
      {icon}
      {text}
    </span>
  )
}

function validateForm(form) {
  const startsAt = new Date(`${form.date}T${form.startTime}:00`)
  const endsAt = new Date(`${form.date}T${form.endTime}:00`)

  if (!form.date || startsAt <= new Date()) {
    return 'Choose a future date and time.'
  }
  if (endsAt <= startsAt) {
    return 'End time must be after start time.'
  }
  if (!form.locationName.trim() || !form.addressLine1.trim() || !form.city.trim() || !form.state.trim() || !form.postalCode.trim()) {
    return 'Complete the location fields.'
  }
  if (!form.positions.length || form.positions.some((position) => Number(position.spots_needed) < 1)) {
    return 'Add at least one valid Sub requirement.'
  }
  const totalSpotsNeeded = form.positions.reduce(
    (sum, position) => sum + Number(position.spots_needed || 0),
    0,
  )
  if (form.positions.length > maxSubRows || totalSpotsNeeded > maxTotalSubs) {
    return `Need a Sub posts can include up to ${maxTotalSubs} total Subs.`
  }
  const positionKeys = new Set()
  for (const position of form.positions) {
    const key = `${position.position_label}:${position.player_group}`
    if (positionKeys.has(key)) {
      return 'Each position and player group row must be unique.'
    }
    positionKeys.add(key)
  }

  return ''
}

function buildCreatePayload(form, totalSpotsNeeded) {
  return {
    sport_type: 'soccer',
    format_label: form.formatLabel,
    skill_level: form.skillLevel,
    game_player_group: form.gamePlayerGroup,
    team_name: null,
    starts_at: new Date(`${form.date}T${form.startTime}:00`).toISOString(),
    ends_at: new Date(`${form.date}T${form.endTime}:00`).toISOString(),
    timezone: 'America/Chicago',
    location_name: form.locationName.trim(),
    address_line_1: form.addressLine1.trim(),
    city: form.city.trim(),
    state: form.state.trim(),
    postal_code: form.postalCode.trim(),
    country_code: 'US',
    neighborhood: form.neighborhood.trim() || null,
    subs_needed: totalSpotsNeeded,
    price_due_at_venue_cents: Math.max(0, Math.round(Number(form.priceDue || 0) * 100)),
    currency: 'USD',
    payment_note: null,
    notes: form.notes.trim() || null,
    positions: form.positions.map((position, index) => ({
      position_label: position.position_label,
      player_group: position.player_group,
      spots_needed: Number(position.spots_needed),
      sort_order: index,
    })),
  }
}

function buildPostHeadline(post) {
  return `Need ${post.subs_needed} ${post.subs_needed === 1 ? 'Sub' : 'Subs'} · ${formatStatus(post.game_player_group)} ${post.format_label} · ${formatStatus(post.skill_level)}`
}

function formatNeedLabel(position) {
  const spots = Number(position.spots_needed || 0)
  const group = formatStatus(position.player_group)
  const label = formatStatus(position.position_label)

  return `${spots} ${spots === 1 ? 'Sub' : 'Subs'} · ${group} · ${label}`
}

function getOwnerPostStatus(post) {
  const pending = Number(post.pending_count || 0)
  const confirmed = Number(post.confirmed_count || 0)

  if (pending > 0) {
    return `${pending} pending`
  }
  return `${confirmed}/${post.subs_needed} confirmed`
}

function formatStatus(value) {
  return String(value || '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function formatTimeRange(post) {
  return `${formatTime(post.starts_at)}-${formatTime(post.ends_at)} · ${getDurationMinutes(post)} min`
}

function getDurationMinutes(post) {
  const startsAt = new Date(post.starts_at)
  const endsAt = new Date(post.ends_at)
  return Math.max(0, Math.round((endsAt - startsAt) / 60000))
}

function formatDate(value) {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value))
}

function formatTime(value) {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

function getDefaultDate() {
  const date = new Date()
  date.setDate(date.getDate() + 3)
  return toDateInputValue(date)
}

function toDateInputValue(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function buildDateOptions() {
  return Array.from({ length: 120 }, (_, index) => {
    const date = new Date()
    date.setDate(date.getDate() + index + 1)
    return {
      value: toDateInputValue(date),
      label: new Intl.DateTimeFormat('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric',
      }).format(date),
    }
  })
}

function buildTimeOptions() {
  const options = []
  for (let hour = 5; hour <= 23; hour += 1) {
    for (let minute = 0; minute < 60; minute += 5) {
      const value = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`
      const date = new Date(`2026-01-01T${value}:00`)
      options.push({
        value,
        label: new Intl.DateTimeFormat('en-US', {
          hour: 'numeric',
          minute: '2-digit',
        }).format(date),
      })
    }
  }
  return options
}

function getDefaultPositionGroup(postGroup) {
  if (postGroup === 'men') {
    return 'men'
  }
  if (postGroup === 'women') {
    return 'women'
  }
  return 'open'
}

function getDefaultPositions(postGroup) {
  return [
    {
      position_label: 'field_player',
      player_group: getDefaultPositionGroup(postGroup),
      spots_needed: 1,
      sort_order: 0,
    },
  ]
}

function hydrateNeedASubForm(post) {
  return {
    date: toDateInputValue(new Date(post.starts_at)),
    startTime: toTimeInputValue(new Date(post.starts_at)),
    endTime: toTimeInputValue(new Date(post.ends_at)),
    formatLabel: post.format_label,
    skillLevel: post.skill_level,
    gamePlayerGroup: post.game_player_group,
    locationName: post.location_name || '',
    addressLine1: post.address_line_1 || '',
    city: post.city || '',
    state: post.state || '',
    postalCode: post.postal_code || '',
    neighborhood: post.neighborhood || '',
    priceDue: Number(post.price_due_at_venue_cents || 0) / 100,
    notes: post.notes || '',
    positions: (post.positions || []).map((position, index) => ({
      position_label: position.position_label,
      player_group: position.player_group,
      spots_needed: position.spots_needed,
      sort_order: index,
    })),
  }
}

function toTimeInputValue(date) {
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function getNextPosition(positions, postGroup) {
  const usedPairs = new Set(
    positions.map((position) => `${position.position_label}:${position.player_group}`),
  )
  const groups = getPositionGroupOptions(postGroup).map((option) => option.value)

  for (const group of groups) {
    for (const position of positionOptions) {
      if (!usedPairs.has(`${position.value}:${group}`)) {
        return {
          position_label: position.value,
          player_group: group,
        }
      }
    }
  }

  return {
    position_label: 'field_player',
    player_group: getDefaultPositionGroup(postGroup),
  }
}

function getPositionGroupOptions(postGroup) {
  if (postGroup === 'men') {
    return [
      { label: 'Open', value: 'open' },
      { label: 'Men', value: 'men' },
    ]
  }

  if (postGroup === 'women') {
    return [
      { label: 'Open', value: 'open' },
      { label: 'Women', value: 'women' },
    ]
  }

  if (postGroup === 'open') {
    return [{ label: 'Open', value: 'open' }]
  }

  return [
    { label: 'Open', value: 'open' },
    { label: 'Men', value: 'men' },
    { label: 'Women', value: 'women' },
  ]
}

function getSpotsLeft(post) {
  const positionTotal = (post.positions || []).reduce((sum, position) => {
    const spotsLeft = Number(position.spots_needed || 0) - countHeldSpots(position)
    return sum + Math.max(0, spotsLeft)
  }, 0)

  if (post.positions?.length) {
    return positionTotal
  }

  return Math.max(0, Number(post.subs_needed || 0) - Number(post.confirmed_count || 0))
}

function countHeldSpots(position) {
  return Number(position.pending_count || 0) + Number(position.confirmed_count || 0)
}

export {
  CreateNeedASubForm,
  buildCreatePayload,
  buildPostHeadline,
  formatDate,
  formatNeedLabel,
  formatStatus,
  formatTime,
  formatTimeRange,
  countHeldSpots,
  getNextPosition,
  getSpotsLeft,
  hydrateNeedASubForm,
  validateForm,
}
export default NeedASubPage
