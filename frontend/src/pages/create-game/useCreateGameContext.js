import { useEffect, useRef, useState } from 'react'
import {
  loadEditableGame,
  loadHostPublishFees,
  loadUserPaymentMethods,
} from './createGameApi.js'
import { initialForm } from './createGameData.js'
import { mapGameToForm } from './createGameMappers.js'

export function useCreateGameContext({
  appUser,
  gameId,
  isEditMode,
  isLoading,
  onVerifiedHostRefresh,
  refreshCurrentUserVerification,
}) {
  const [form, setForm] = useState(initialForm)
  const [formBaseline, setFormBaseline] = useState(initialForm)
  const [currentUser, setCurrentUser] = useState(null)
  const [paymentMethod, setPaymentMethod] = useState(null)
  const [firstPublishIsFree, setFirstPublishIsFree] = useState(true)
  const [communityGameDetailId, setCommunityGameDetailId] = useState('')
  const [createdGameId, setCreatedGameId] = useState('')
  const [loadError, setLoadError] = useState('')
  const blockedVerificationRefreshRef = useRef('')

  useEffect(() => {
    let ignore = false

    async function loadVerifiedContext(effectiveAppUser) {
      const [paymentMethods, gameContext, hostPublishFees] = await Promise.all([
        loadUserPaymentMethods(effectiveAppUser.id),
        isEditMode ? loadEditableGame(gameId) : Promise.resolve(null),
        loadHostPublishFees(effectiveAppUser.id),
      ])

      if (ignore) {
        return
      }

      setCurrentUser(effectiveAppUser)
      setPaymentMethod(paymentMethods.find((method) => method.is_default) || paymentMethods[0] || null)
      setFirstPublishIsFree(
        !hostPublishFees.some((fee) => fee.waiver_reason === 'first_game_free'),
      )

      if (gameContext) {
        const editableForm = mapGameToForm(
          gameContext.game,
          gameContext.venue,
          gameContext.communityDetails,
        )
        setCommunityGameDetailId(gameContext.communityDetails?.id || '')
        setForm(editableForm)
        setFormBaseline(editableForm)
      } else {
        setCommunityGameDetailId('')
        setForm(initialForm)
        setFormBaseline(initialForm)
      }
    }

    async function refreshBlockedHost() {
      const refreshedAppUser = await refreshCurrentUserVerification().catch(() => null)

      if (!refreshedAppUser?.email_verified_at || ignore) {
        return
      }

      onVerifiedHostRefresh(refreshedAppUser.id)
      await loadVerifiedContext(refreshedAppUser)
    }

    async function loadCreateGameContext() {
      try {
        if (isLoading) {
          return
        }

        if (!appUser?.id) {
          throw new Error('Sign in to create a game.')
        }

        if (!ignore) {
          setLoadError('')
          setCurrentUser(appUser)
        }

        if (!isEditMode && !appUser.email_verified_at) {
          if (!ignore) {
            setPaymentMethod(null)
            setFirstPublishIsFree(true)
            setCommunityGameDetailId('')
            setCreatedGameId('')
            setForm(initialForm)
            setFormBaseline(initialForm)
          }

          if (blockedVerificationRefreshRef.current !== appUser.id) {
            blockedVerificationRefreshRef.current = appUser.id
            refreshBlockedHost()
          }
          return
        }

        blockedVerificationRefreshRef.current = ''
        await loadVerifiedContext(appUser)
      } catch (error) {
        if (!ignore) {
          setLoadError(error instanceof Error ? error.message : 'Unable to load create game data.')
        }
      }
    }

    loadCreateGameContext()

    return () => {
      ignore = true
    }
  }, [
    appUser,
    gameId,
    isEditMode,
    isLoading,
    onVerifiedHostRefresh,
    refreshCurrentUserVerification,
  ])

  return {
    communityGameDetailId,
    createdGameId,
    currentUser,
    firstPublishIsFree,
    form,
    formBaseline,
    loadError,
    paymentMethod,
    setCreatedGameId,
    setForm,
  }
}
