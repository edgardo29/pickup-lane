export function getFilteredSections(activeFilter, appNotifications, gameNotifications) {
  const sections = [
    {
      description: 'Important updates and support messages.',
      items: appNotifications,
      key: 'app',
      title: 'App Notifications',
    },
    {
      description: 'Game chat and activity from games you joined or host.',
      items: gameNotifications,
      key: 'game',
      title: 'Game Activity',
    },
  ]

  return sections.filter((section) => section.key === activeFilter)
}
