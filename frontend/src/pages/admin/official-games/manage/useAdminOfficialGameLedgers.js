import { useEffect, useState } from 'react'
import {
  getAdminOfficialGameMoney,
  listAdminOfficialGameBookings,
  listAdminOfficialGameWaitlist,
} from '../shared/adminOfficialGamesApi.js'

const emptyMoneyLedger = {
  payments: [],
  refunds: [],
  credits: [],
  credit_usages: [],
}

export function useAdminOfficialGameLedgers({
  canViewMoneyData,
  currentUser,
  gameId,
  isAdminAccessLoading,
}) {
  const currentContextKey = currentUser ? `${currentUser.uid}:${gameId}` : ''
  const [bookings, setBookings] = useState([])
  const [bookingsContextKey, setBookingsContextKey] = useState('')
  const [bookingsError, setBookingsError] = useState('')
  const [bookingsLoadState, setBookingsLoadState] = useState('idle')
  const [bookingsRefreshCount, setBookingsRefreshCount] = useState(0)
  const [waitlistEntries, setWaitlistEntries] = useState([])
  const [waitlistContextKey, setWaitlistContextKey] = useState('')
  const [waitlistError, setWaitlistError] = useState('')
  const [waitlistLoadState, setWaitlistLoadState] = useState('idle')
  const [waitlistRefreshCount, setWaitlistRefreshCount] = useState(0)
  const [moneyLedger, setMoneyLedger] = useState(emptyMoneyLedger)
  const [moneyContextKey, setMoneyContextKey] = useState('')
  const [moneyError, setMoneyError] = useState('')
  const [moneyLoadState, setMoneyLoadState] = useState('idle')
  const [moneyRefreshCount, setMoneyRefreshCount] = useState(0)

  useEffect(() => {
    if (isAdminAccessLoading || !currentUser) {
      return undefined
    }
    if (!canViewMoneyData) {
      return undefined
    }

    let isMounted = true
    async function loadBookings() {
      setBookings([])
      setBookingsError('')
      setBookingsLoadState('loading')

      try {
        const nextBookings = await listAdminOfficialGameBookings({
          firebaseUser: currentUser,
          gameId,
        })
        if (!isMounted) {
          return
        }
        setBookingsContextKey(currentContextKey)
        setBookings(nextBookings ?? [])
        setBookingsLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }
        setBookingsContextKey(currentContextKey)
        setBookings([])
        setBookingsError(error.message || 'Bookings could not be loaded.')
        setBookingsLoadState('error')
      }
    }

    loadBookings()

    return () => {
      isMounted = false
    }
  }, [
    bookingsRefreshCount,
    canViewMoneyData,
    currentContextKey,
    currentUser,
    gameId,
    isAdminAccessLoading,
  ])

  useEffect(() => {
    if (isAdminAccessLoading || !currentUser) {
      return undefined
    }
    if (!canViewMoneyData) {
      return undefined
    }

    let isMounted = true
    async function loadWaitlist() {
      setWaitlistEntries([])
      setWaitlistError('')
      setWaitlistLoadState('loading')

      try {
        const nextWaitlistEntries = await listAdminOfficialGameWaitlist({
          firebaseUser: currentUser,
          gameId,
        })
        if (!isMounted) {
          return
        }
        setWaitlistContextKey(currentContextKey)
        setWaitlistEntries(nextWaitlistEntries ?? [])
        setWaitlistLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }
        setWaitlistContextKey(currentContextKey)
        setWaitlistEntries([])
        setWaitlistError(error.message || 'Waitlist could not be loaded.')
        setWaitlistLoadState('error')
      }
    }

    loadWaitlist()

    return () => {
      isMounted = false
    }
  }, [
    canViewMoneyData,
    currentContextKey,
    currentUser,
    gameId,
    isAdminAccessLoading,
    waitlistRefreshCount,
  ])

  useEffect(() => {
    if (isAdminAccessLoading || !currentUser) {
      return undefined
    }
    if (!canViewMoneyData) {
      return undefined
    }

    let isMounted = true
    async function loadMoneyLedger() {
      setMoneyLedger(emptyMoneyLedger)
      setMoneyError('')
      setMoneyLoadState('loading')

      try {
        const nextMoneyLedger = await getAdminOfficialGameMoney({
          firebaseUser: currentUser,
          gameId,
        })
        if (!isMounted) {
          return
        }
        setMoneyContextKey(currentContextKey)
        setMoneyLedger(nextMoneyLedger ?? emptyMoneyLedger)
        setMoneyLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }
        setMoneyContextKey(currentContextKey)
        setMoneyLedger(emptyMoneyLedger)
        setMoneyError(error.message || 'Money ledger could not be loaded.')
        setMoneyLoadState('error')
      }
    }

    loadMoneyLedger()

    return () => {
      isMounted = false
    }
  }, [
    canViewMoneyData,
    currentContextKey,
    currentUser,
    gameId,
    isAdminAccessLoading,
    moneyRefreshCount,
  ])

  const canLoadCurrentContext = (
    canViewMoneyData
    && !isAdminAccessLoading
    && Boolean(currentUser)
  )
  const bookingsAreCurrent = bookingsContextKey === currentContextKey
  const waitlistIsCurrent = waitlistContextKey === currentContextKey
  const moneyIsCurrent = moneyContextKey === currentContextKey

  return {
    bookings: bookingsAreCurrent ? bookings : [],
    bookingsError: bookingsAreCurrent ? bookingsError : '',
    bookingsLoadState: bookingsAreCurrent
      ? bookingsLoadState
      : canLoadCurrentContext ? 'loading' : 'idle',
    moneyError: moneyIsCurrent ? moneyError : '',
    moneyLedger: moneyIsCurrent ? moneyLedger : emptyMoneyLedger,
    moneyLoadState: moneyIsCurrent
      ? moneyLoadState
      : canLoadCurrentContext ? 'loading' : 'idle',
    refreshAll: () => {
      setBookingsRefreshCount((count) => count + 1)
      setWaitlistRefreshCount((count) => count + 1)
      setMoneyRefreshCount((count) => count + 1)
    },
    retryBookings: () => setBookingsRefreshCount((count) => count + 1),
    retryMoney: () => setMoneyRefreshCount((count) => count + 1),
    retryWaitlist: () => setWaitlistRefreshCount((count) => count + 1),
    waitlistEntries: waitlistIsCurrent ? waitlistEntries : [],
    waitlistError: waitlistIsCurrent ? waitlistError : '',
    waitlistLoadState: waitlistIsCurrent
      ? waitlistLoadState
      : canLoadCurrentContext ? 'loading' : 'idle',
  }
}
