import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../../hooks/useAuth.js'
import { emptySettings, emptyStats } from './profileData.js'
import { loadProfileData } from './profileApi.js'

export function useProfileContext() {
  const { appUser, isLoading } = useAuth()
  const [currentUser, setCurrentUser] = useState(null)
  const [settings, setSettings] = useState(emptySettings)
  const [stats, setStats] = useState(emptyStats)
  const [paymentMethods, setPaymentMethods] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    let ignore = false

    async function loadProfileContext() {
      setStatus('loading')
      setError('')

      try {
        if (isLoading) {
          return
        }

        if (!appUser?.id) {
          throw new Error('Sign in to view your profile.')
        }

        const profileData = await loadProfileData(appUser.id)

        if (!ignore) {
          setCurrentUser(appUser)
          setSettings(profileData.settings)
          setStats(profileData.stats)
          setPaymentMethods(profileData.paymentMethods)
          setStatus('success')
        }
      } catch (requestError) {
        if (!ignore) {
          setError(requestError instanceof Error ? requestError.message : 'Unable to load profile.')
          setStatus('error')
        }
      }
    }

    loadProfileContext()

    return () => {
      ignore = true
    }
  }, [appUser, isLoading])

  return useMemo(
    () => ({ currentUser, error, paymentMethods, settings, stats, status }),
    [currentUser, error, paymentMethods, settings, stats, status],
  )
}
