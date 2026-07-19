import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  CalendarClock,
  ClipboardList,
  Image,
  MapPin,
  ShieldCheck,
} from 'lucide-react'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminActionCenter.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { fetchAdminActionCenter } from '../shared/adminApi.js'

const sectionIconByKey = {
  official_games: ShieldCheck,
  review_cases: ClipboardList,
}

const itemIconByType = {
  official_game_missing_host: ShieldCheck,
  official_game_missing_primary_venue_photo: Image,
  review_case: ClipboardList,
}

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

function formatItemTime(value) {
  if (!value) {
    return 'No date'
  }

  return dateFormatter.format(new Date(value))
}

function countItems(sections) {
  return sections.reduce((total, section) => total + section.items.length, 0)
}

function AdminActionCenterItem({ item }) {
  const ItemIcon = itemIconByType[item.item_type] || ShieldCheck

  return (
    <Link className="admin-action-center-row" to={item.action_path}>
      <div className="admin-action-center-row__icon" aria-hidden="true">
        <ItemIcon />
      </div>
      <div className="admin-action-center-row__copy">
        <strong>{item.title}</strong>
        <span>{item.summary}</span>
        <div className="admin-action-center-row__facts">
          <span><CalendarClock />{formatItemTime(item.due_at)}</span>
          {item.related_entity_label && (
            <span><MapPin />{item.related_entity_label}</span>
          )}
        </div>
      </div>
      <div className="admin-action-center-row__action">
        <em>{item.severity}</em>
        <span>{item.action_label}<ArrowRight /></span>
      </div>
    </Link>
  )
}

function AdminActionCenterSection({ section }) {
  const SectionIcon = sectionIconByKey[section.section_key] || ShieldCheck

  return (
    <section className="admin-action-center-panel" aria-label={section.label}>
      <div className="admin-action-center-panel__heading">
        <div>
          <SectionIcon />
          <h2>{section.label}</h2>
        </div>
        <em>{section.items.length}</em>
      </div>
      <div className="admin-action-center-list">
        {section.items.map((item) => (
          <AdminActionCenterItem item={item} key={item.item_id} />
        ))}
      </div>
    </section>
  )
}

function AdminActionCenterPage() {
  const { currentUser } = useAuth()
  const [actionCenter, setActionCenter] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')

  useEffect(() => {
    let isMounted = true

    async function loadActionCenter() {
      setLoadState('loading')
      setPageError('')

      try {
        const nextActionCenter = await fetchAdminActionCenter({ firebaseUser: currentUser })

        if (!isMounted) {
          return
        }

        setActionCenter(nextActionCenter)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setPageError(error.message || 'Action Center could not be loaded.')
        setLoadState('error')
      }
    }

    loadActionCenter()

    return () => {
      isMounted = false
    }
  }, [currentUser])

  const sections = useMemo(() => actionCenter?.sections ?? [], [actionCenter])
  const totalCount = useMemo(() => countItems(sections), [sections])

  return (
    <>
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'Action Center']}
        description="Review operational items that need staff attention."
        icon={ShieldCheck}
        title="Action Center"
      >
        <div className="admin-action-center-layout">
          <section className="admin-action-center-panel admin-action-center-panel--summary" aria-label="Action Center summary">
            <div className="admin-action-center-panel__heading">
              <div>
                <ShieldCheck />
                <h2>Current work</h2>
              </div>
              <em>{totalCount}</em>
            </div>

            {pageError && <p className="admin-action-center-alert">{pageError}</p>}
            {loadState === 'loading' && (
              <p className="admin-action-center-empty">Loading Action Center.</p>
            )}
            {loadState === 'ready' && totalCount === 0 && (
              <div className="admin-action-center-empty-state">
                <strong>No action items</strong>
                <span>Everything current is clear.</span>
              </div>
            )}
          </section>

          {loadState === 'ready' && sections.map((section) => (
            <AdminActionCenterSection section={section} key={section.section_key} />
          ))}
        </div>
      </AdminWorkspaceLayout>
    </>
  )
}

export default AdminActionCenterPage
