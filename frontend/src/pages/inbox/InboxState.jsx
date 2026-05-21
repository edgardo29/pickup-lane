import { ChatIcon } from '../../components/BrowseIcons.jsx'

export function InboxState({ title, message }) {
  return (
    <section className="inbox-state">
      <ChatIcon />
      <h2>{title}</h2>
      {message && <p>{message}</p>}
    </section>
  )
}
