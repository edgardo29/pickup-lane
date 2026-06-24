import { useEffect, useMemo, useState } from 'react'
import {
  BellRing,
  ChevronLeft,
  ChevronRight,
  FilePenLine,
  Megaphone,
  Plus,
  RefreshCw,
  Save,
  Search,
  UserPlus,
  X,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminPlatformNotices.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import AdminPlatformNoticeDeliveryPanel from './AdminPlatformNoticeDeliveryPanel.jsx'
import {
  createPlatformNoticeCampaign,
  getPlatformNoticeCampaign,
  listAdminUsers,
  listPlatformNoticeCampaigns,
  updatePlatformNoticeCampaign,
} from '../shared/adminApi.js'
import {
  EMPTY_PLATFORM_NOTICE_FILTERS,
  EMPTY_PLATFORM_NOTICE_FORM,
  PLATFORM_NOTICE_STATUS_OPTIONS,
  buildPlatformNoticePayload,
  createPlatformNoticeIdempotencyKey,
  formatPlatformNoticeDateTime,
  formatPlatformNoticeLabel,
  mapPlatformNoticeCampaignToForm,
  shortPlatformNoticeId,
  validatePlatformNoticeForm,
} from './adminPlatformNoticeData.js'

const PAGE_LIMIT = 30

function campaignTargetLabel(campaign) {
  if (campaign.audience_type === 'all_active_users') {
    return 'All active users'
  }

  const count = campaign.target_user_count || 0
  return `${count} selected ${count === 1 ? 'user' : 'users'}`
}

function fallbackSelectedUsers(campaign) {
  return (campaign?.target_user_ids || []).map((userId) => ({
    account_status: 'active',
    display_name: `User ${shortPlatformNoticeId(userId)}`,
    email: '',
    id: userId,
  }))
}

function CampaignListLoading() {
  return (
    <div className="admin-platform-notices-loading" role="status">
      {Array.from({ length: 5 }).map((_, index) => (
        <div className="admin-platform-notices-loading__row" key={index}>
          <SkeletonBlock height="0.86rem" rounded width="58%" />
          <SkeletonBlock height="0.7rem" rounded width="72%" />
          <SkeletonBlock height="0.7rem" rounded width="40%" />
        </div>
      ))}
    </div>
  )
}

function CampaignStatus({ status }) {
  return (
    <span className={`admin-platform-notices-status admin-platform-notices-status--${status}`}>
      {formatPlatformNoticeLabel(status)}
    </span>
  )
}

function CampaignRow({ campaign, isSelected, onSelect }) {
  return (
    <button
      className={`admin-platform-notices-row ${isSelected ? 'is-active' : ''}`}
      type="button"
      onClick={() => onSelect(campaign.id)}
    >
      <span className="admin-platform-notices-row__icon" aria-hidden="true">
        <Megaphone />
      </span>
      <span className="admin-platform-notices-row__copy">
        <strong>{campaign.internal_name}</strong>
        <span>{campaign.title}</span>
        <small>{formatPlatformNoticeDateTime(campaign.updated_at)}</small>
      </span>
      <span className="admin-platform-notices-row__meta">
        <CampaignStatus status={campaign.campaign_status} />
        <span>{campaignTargetLabel(campaign)}</span>
      </span>
    </button>
  )
}

function SegmentedChoice({ disabled, label, onChange, options, value }) {
  return (
    <fieldset className="admin-platform-notices-segmented">
      <legend>{label}</legend>
      <div>
        {options.map((option) => (
          <button
            aria-pressed={value === option.value}
            className={value === option.value ? 'is-active' : ''}
            disabled={disabled}
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </fieldset>
  )
}

function SelectedAudienceEditor({
  currentUser,
  disabled,
  onAddUser,
  onRemoveUser,
  selectedUsers,
}) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [searchError, setSearchError] = useState('')
  const [searchState, setSearchState] = useState('idle')
  const selectedIds = useMemo(
    () => new Set(selectedUsers.map((user) => user.id)),
    [selectedUsers],
  )

  async function handleSearch(event) {
    event.preventDefault()
    const normalizedQuery = query.trim()
    if (!normalizedQuery || disabled || !currentUser) {
      return
    }

    setSearchState('loading')
    setSearchError('')
    try {
      const users = await listAdminUsers({
        accountStatus: 'active',
        firebaseUser: currentUser,
        limit: 20,
        query: normalizedQuery,
      })
      setResults(users.filter((user) => !selectedIds.has(user.id)))
      setSearchState('ready')
    } catch (error) {
      setResults([])
      setSearchError(error.message || 'Users could not be searched.')
      setSearchState('error')
    }
  }

  function addUser(user) {
    onAddUser(user)
    setResults((current) => current.filter((item) => item.id !== user.id))
  }

  return (
    <div className="admin-platform-notices-audience-editor">
      <form className="admin-platform-notices-user-search" onSubmit={handleSearch}>
        <label>
          <span>Find active users</span>
          <input
            disabled={disabled}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <button
          aria-label="Search active users"
          disabled={disabled || !query.trim() || searchState === 'loading'}
          title="Search users"
          type="submit"
        >
          <Search />
        </button>
      </form>

      <FormErrorMessage>{searchError}</FormErrorMessage>

      {searchState === 'ready' && results.length === 0 && (
        <p className="admin-platform-notices-inline-empty">No active users found.</p>
      )}
      {results.length > 0 && (
        <div className="admin-platform-notices-user-results">
          {results.map((user) => (
            <button key={user.id} type="button" onClick={() => addUser(user)}>
              <span>
                <strong>{user.display_name}</strong>
                <small>{user.email || user.id}</small>
              </span>
              <UserPlus aria-hidden="true" />
            </button>
          ))}
        </div>
      )}

      <div className="admin-platform-notices-selected-users">
        <div>
          <span>Selected recipients</span>
          <strong>{selectedUsers.length}</strong>
        </div>
        {selectedUsers.length === 0 ? (
          <p className="admin-platform-notices-inline-empty">No users selected.</p>
        ) : (
          <ul>
            {selectedUsers.map((user) => (
              <li key={user.id}>
                <span>
                  <strong>{user.display_name}</strong>
                  <small>{user.email || user.id}</small>
                </span>
                <button
                  aria-label={`Remove ${user.display_name}`}
                  disabled={disabled}
                  title="Remove recipient"
                  type="button"
                  onClick={() => onRemoveUser(user.id)}
                >
                  <X />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function CampaignPreview({ form, selectedUserCount }) {
  const targetText = form.audienceType === 'all_active_users'
    ? 'All active users'
    : `${selectedUserCount} selected ${selectedUserCount === 1 ? 'user' : 'users'}`

  return (
    <section className="admin-platform-notices-preview">
      <div>
        <BellRing aria-hidden="true" />
        <span>Pickup Lane</span>
      </div>
      <h3>{form.title.trim() || 'Notice title'}</h3>
      <strong>{form.summary.trim() || 'Notice summary'}</strong>
      <p>{form.body.trim() || 'Notice body preview.'}</p>
      <footer>
        <span>{targetText}</span>
        <span>{formatPlatformNoticeLabel(form.deliveryClass)}</span>
      </footer>
    </section>
  )
}

function CampaignEditor({
  campaign,
  currentUser,
  editorMode,
  onCampaignSaved,
}) {
  const [form, setForm] = useState(() => (
    editorMode === 'create'
      ? EMPTY_PLATFORM_NOTICE_FORM
      : mapPlatformNoticeCampaignToForm(campaign)
  ))
  const [idempotencyKey] = useState(createPlatformNoticeIdempotencyKey)
  const [saveError, setSaveError] = useState('')
  const [saveState, setSaveState] = useState('idle')
  const [selectedUsers, setSelectedUsers] = useState(() => (
    editorMode === 'create' ? [] : fallbackSelectedUsers(campaign)
  ))

  const isDraft = editorMode === 'create' || campaign?.campaign_status === 'draft'
  const isSaving = saveState === 'saving'

  function updateForm(field, value) {
    setSaveError('')
    setSaveState('idle')
    setForm((current) => ({
      ...current,
      [field]: value,
    }))
    if (field === 'audienceType' && value === 'all_active_users') {
      setSelectedUsers([])
    }
  }

  function addSelectedUser(user) {
    setSaveError('')
    setSelectedUsers((current) => (
      current.some((item) => item.id === user.id) ? current : [...current, user]
    ))
  }

  function removeSelectedUser(userId) {
    setSaveError('')
    setSelectedUsers((current) => current.filter((user) => user.id !== userId))
  }

  async function handleSave(event) {
    event.preventDefault()
    const validationError = validatePlatformNoticeForm(form, selectedUsers)
    if (validationError) {
      setSaveError(validationError)
      return
    }

    setSaveState('saving')
    setSaveError('')
    try {
      const payload = buildPlatformNoticePayload({
        form,
        idempotencyKey: editorMode === 'create' ? idempotencyKey : '',
        selectedUsers,
      })
      const savedCampaign = editorMode === 'create'
        ? await createPlatformNoticeCampaign({ firebaseUser: currentUser, payload })
        : await updatePlatformNoticeCampaign({
          campaignId: campaign.id,
          firebaseUser: currentUser,
          payload,
        })

      setSaveState('saved')
      onCampaignSaved(savedCampaign)
    } catch (error) {
      setSaveError(error.message || 'Campaign could not be saved.')
      setSaveState('error')
    }
  }

  if (editorMode === 'detail' && !campaign) {
    return (
      <div className="admin-platform-notices-empty">
        <Megaphone />
        <strong>No campaign selected</strong>
        <span>Select a campaign or create a draft.</span>
      </div>
    )
  }

  return (
    <form className="admin-platform-notices-form" onSubmit={handleSave}>
      <div className="admin-platform-notices-editor-heading">
        <div>
          <FilePenLine />
          <div>
            <h2>{editorMode === 'create' ? 'New Campaign Draft' : campaign.internal_name}</h2>
            <span>
              {editorMode === 'create'
                ? 'Unsaved draft'
                : `Updated ${formatPlatformNoticeDateTime(campaign.updated_at)}`}
            </span>
          </div>
        </div>
        {campaign && <CampaignStatus status={campaign.campaign_status} />}
      </div>

      {!isDraft && (
        <p className="admin-platform-notices-readonly">
          This campaign is no longer a draft and cannot be edited.
        </p>
      )}

      <div className="admin-platform-notices-form-grid">
        <label className="admin-platform-notices-field admin-platform-notices-field--wide">
          <span>Internal name</span>
          <input
            disabled={!isDraft || isSaving}
            maxLength={160}
            value={form.internalName}
            onChange={(event) => updateForm('internalName', event.target.value)}
          />
        </label>
        <label className="admin-platform-notices-field">
          <span>Inbox title</span>
          <input
            disabled={!isDraft || isSaving}
            maxLength={150}
            value={form.title}
            onChange={(event) => updateForm('title', event.target.value)}
          />
        </label>
        <label className="admin-platform-notices-field">
          <span>Summary</span>
          <input
            disabled={!isDraft || isSaving}
            maxLength={500}
            value={form.summary}
            onChange={(event) => updateForm('summary', event.target.value)}
          />
        </label>
        <label className="admin-platform-notices-field admin-platform-notices-field--wide">
          <span>Body</span>
          <textarea
            disabled={!isDraft || isSaving}
            maxLength={4000}
            rows={5}
            value={form.body}
            onChange={(event) => updateForm('body', event.target.value)}
          />
          <small>{form.body.length}/4000</small>
        </label>
      </div>

      <div className="admin-platform-notices-choice-grid">
        <SegmentedChoice
          disabled={!isDraft || isSaving}
          label="Audience"
          value={form.audienceType}
          options={[
            { label: 'All active users', value: 'all_active_users' },
            { label: 'Selected users', value: 'selected_users' },
          ]}
          onChange={(value) => updateForm('audienceType', value)}
        />
        <SegmentedChoice
          disabled={!isDraft || isSaving}
          label="Delivery class"
          value={form.deliveryClass}
          options={[
            { label: 'Mandatory', value: 'mandatory' },
            { label: 'Preference controlled', value: 'preference_controlled' },
          ]}
          onChange={(value) => updateForm('deliveryClass', value)}
        />
      </div>

      {form.audienceType === 'selected_users' && (
        <SelectedAudienceEditor
          currentUser={currentUser}
          disabled={!isDraft || isSaving}
          onAddUser={addSelectedUser}
          onRemoveUser={removeSelectedUser}
          selectedUsers={selectedUsers}
        />
      )}

      <CampaignPreview form={form} selectedUserCount={selectedUsers.length} />

      <FormErrorMessage>{saveError}</FormErrorMessage>
      {saveState === 'saved' && (
        <p className="admin-platform-notices-success">Draft saved.</p>
      )}

      <div className="admin-platform-notices-form-actions">
        <button
          className="admin-platform-notices-button admin-platform-notices-button--primary"
          disabled={!isDraft || isSaving}
          type="submit"
        >
          <Save />
          {isSaving ? 'Saving' : editorMode === 'create' ? 'Create Draft' : 'Save Draft'}
        </button>
      </div>
    </form>
  )
}

function AdminPlatformNoticesPage() {
  const { currentUser } = useAuth()
  const [campaigns, setCampaigns] = useState([])
  const [detailCampaign, setDetailCampaign] = useState(null)
  const [detailError, setDetailError] = useState('')
  const [detailState, setDetailState] = useState('idle')
  const [draftFilters, setDraftFilters] = useState(EMPTY_PLATFORM_NOTICE_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_PLATFORM_NOTICE_FILTERS)
  const [editorMode, setEditorMode] = useState('detail')
  const [listError, setListError] = useState('')
  const [listState, setListState] = useState('loading')
  const [offset, setOffset] = useState(0)
  const [refreshCount, setRefreshCount] = useState(0)
  const [selectedCampaignId, setSelectedCampaignId] = useState(null)
  const [totalCount, setTotalCount] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadCampaigns() {
      if (!currentUser) {
        return
      }

      setListState('loading')
      setListError('')
      try {
        const response = await listPlatformNoticeCampaigns({
          firebaseUser: currentUser,
          limit: PAGE_LIMIT,
          offset,
          ...appliedFilters,
        })
        if (!isMounted) {
          return
        }

        const nextCampaigns = response.campaigns || []
        const nextTotal = response.total_count || 0
        if (!nextCampaigns.length && offset > 0 && nextTotal > 0) {
          setOffset(Math.max(0, offset - PAGE_LIMIT))
          return
        }

        setCampaigns(nextCampaigns)
        setTotalCount(nextTotal)
        setSelectedCampaignId((currentId) => {
          if (editorMode === 'create') {
            return currentId
          }
          return nextCampaigns.some((campaign) => campaign.id === currentId)
            ? currentId
            : nextCampaigns[0]?.id || null
        })
        if (!nextCampaigns.length && editorMode !== 'create') {
          setEditorMode('create')
        }
        setListState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }
        setCampaigns([])
        setTotalCount(0)
        setListError(error.message || 'Campaigns could not be loaded.')
        setListState('error')
      }
    }

    loadCampaigns()
    return () => {
      isMounted = false
    }
  }, [appliedFilters, currentUser, editorMode, offset, refreshCount])

  useEffect(() => {
    let isMounted = true

    async function loadDetail() {
      if (!currentUser || !selectedCampaignId || editorMode === 'create') {
        setDetailCampaign(null)
        setDetailError('')
        setDetailState('idle')
        return
      }

      setDetailState('loading')
      setDetailError('')
      try {
        const campaign = await getPlatformNoticeCampaign({
          campaignId: selectedCampaignId,
          firebaseUser: currentUser,
        })
        if (isMounted) {
          setDetailCampaign(campaign)
          setDetailState('ready')
        }
      } catch (error) {
        if (isMounted) {
          setDetailCampaign(null)
          setDetailError(error.message || 'Campaign detail could not be loaded.')
          setDetailState('error')
        }
      }
    }

    loadDetail()
    return () => {
      isMounted = false
    }
  }, [currentUser, editorMode, selectedCampaignId])

  function selectCampaign(campaignId) {
    setEditorMode('detail')
    setSelectedCampaignId(campaignId)
  }

  function startNewCampaign() {
    setEditorMode('create')
    setSelectedCampaignId(null)
    setDetailCampaign(null)
  }

  function applyFilters(event) {
    event.preventDefault()
    setOffset(0)
    setAppliedFilters({
      campaignStatus: draftFilters.campaignStatus,
      search: draftFilters.search.trim(),
    })
  }

  function handleCampaignSaved(campaign) {
    setEditorMode('detail')
    setSelectedCampaignId(campaign.id)
    setDetailCampaign(campaign)
    setRefreshCount((count) => count + 1)
  }

  function handleCampaignDeliveryUpdated(campaign) {
    setDetailCampaign(campaign)
    setRefreshCount((count) => count + 1)
  }

  const pageStart = totalCount ? offset + 1 : 0
  const pageEnd = Math.min(offset + campaigns.length, totalCount)

  return (
    <>
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'System', 'Platform Notices']}
        description="Create, review, send, and monitor platform notices."
        icon={Megaphone}
        title="Platform Notices"
      >
        <div className="admin-platform-notices-layout">
          <section className="admin-platform-notices-panel">
            <div className="admin-platform-notices-panel__heading">
              <div>
                <Megaphone />
                <h2>Campaigns</h2>
              </div>
              <button
                aria-label="Create campaign draft"
                title="New draft"
                type="button"
                onClick={startNewCampaign}
              >
                <Plus />
              </button>
            </div>

            <form className="admin-platform-notices-filters" onSubmit={applyFilters}>
              <label>
                <span>Search</span>
                <input
                  value={draftFilters.search}
                  onChange={(event) => setDraftFilters((current) => ({
                    ...current,
                    search: event.target.value,
                  }))}
                />
              </label>
              <label>
                <span>Status</span>
                <select
                  value={draftFilters.campaignStatus}
                  onChange={(event) => setDraftFilters((current) => ({
                    ...current,
                    campaignStatus: event.target.value,
                  }))}
                >
                  {PLATFORM_NOTICE_STATUS_OPTIONS.map((option) => (
                    <option key={option.value || 'all'} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <button aria-label="Search campaigns" title="Search campaigns" type="submit">
                <Search />
              </button>
              <button
                aria-label="Refresh campaigns"
                title="Refresh campaigns"
                type="button"
                onClick={() => setRefreshCount((count) => count + 1)}
              >
                <RefreshCw />
              </button>
            </form>

            <FormErrorMessage>{listError}</FormErrorMessage>
            {listState === 'loading' && <CampaignListLoading />}
            {listState === 'ready' && campaigns.length === 0 && (
              <div className="admin-platform-notices-empty admin-platform-notices-empty--list">
                <Megaphone />
                <strong>No campaigns found</strong>
                <span>Create a draft or change the filters.</span>
              </div>
            )}
            {campaigns.length > 0 && (
              <div className="admin-platform-notices-list">
                {campaigns.map((campaign) => (
                  <CampaignRow
                    campaign={campaign}
                    isSelected={
                      editorMode === 'detail' && campaign.id === selectedCampaignId
                    }
                    key={campaign.id}
                    onSelect={selectCampaign}
                  />
                ))}
              </div>
            )}

            {totalCount > 0 && (
              <nav className="admin-platform-notices-pagination">
                <span>{pageStart}-{pageEnd} of {totalCount}</span>
                <div>
                  <button
                    aria-label="Previous campaign page"
                    disabled={offset === 0}
                    title="Previous page"
                    type="button"
                    onClick={() => setOffset(Math.max(0, offset - PAGE_LIMIT))}
                  >
                    <ChevronLeft />
                  </button>
                  <button
                    aria-label="Next campaign page"
                    disabled={offset + campaigns.length >= totalCount}
                    title="Next page"
                    type="button"
                    onClick={() => setOffset(offset + PAGE_LIMIT)}
                  >
                    <ChevronRight />
                  </button>
                </div>
              </nav>
            )}
          </section>

          <section className="admin-platform-notices-panel admin-platform-notices-panel--editor">
            {detailState === 'loading' ? (
              <div className="admin-platform-notices-editor-loading">
                <SkeletonBlock height="1rem" rounded width="42%" />
                <SkeletonBlock height="2.5rem" rounded width="100%" />
                <SkeletonBlock height="8rem" rounded width="100%" />
              </div>
            ) : (
              <>
                <FormErrorMessage>{detailError}</FormErrorMessage>
                <CampaignEditor
                  campaign={detailCampaign}
                  currentUser={currentUser}
                  editorMode={editorMode}
                  key={`${editorMode}-${detailCampaign?.id || 'new'}`}
                  onCampaignSaved={handleCampaignSaved}
                />
                {editorMode === 'detail' && detailCampaign && (
                  <AdminPlatformNoticeDeliveryPanel
                    campaign={detailCampaign}
                    currentUser={currentUser}
                    key={detailCampaign.id}
                    onCampaignUpdated={handleCampaignDeliveryUpdated}
                  />
                )}
              </>
            )}
          </section>
        </div>
      </AdminWorkspaceLayout>
    </>
  )
}

export default AdminPlatformNoticesPage
