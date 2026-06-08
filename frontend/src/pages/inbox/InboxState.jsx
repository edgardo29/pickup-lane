import { ChatIcon } from '../../components/BrowseIcons.jsx'

export function InboxState({ compact = false, title, message }) {
  return (
    <section className={compact ? 'inbox-state inbox-state--compact' : 'inbox-state'}>
      <ChatIcon />
      <h2>{title}</h2>
      {message && <p>{message}</p>}
    </section>
  )
}
