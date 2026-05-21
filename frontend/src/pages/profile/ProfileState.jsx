import { UserIcon } from '../../components/BrowseIcons.jsx'

export function ProfileState({ title, message }) {
  return (
    <section className="profile-state">
      <UserIcon />
      <h1>{title}</h1>
      {message && <p>{message}</p>}
    </section>
  )
}
