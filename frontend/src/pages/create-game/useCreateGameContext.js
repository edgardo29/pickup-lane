import { useEffect, useRef, useState } from 'react'
import {
  loadEditableGame,
  loadHostPublishFees,
  loadUserPaymentMethods,
} from './createGameApi.js'
import { useVerificationFormState } from '../../features/email-verification/useVerificationFormState.js'
import { initialForm } from './createGameData.js'
import { mapGameToForm } from './createGameMappers.js'

export function useCreateGameContext({
  appUser,
  firebaseUser,
  gameId,
  isEditMode,
  isLoading,
  onVerifiedHostRefresh,
  refreshCurrentUserVerification,
}) {
  const { form, setForm, preserveForVerification } = useVerificationFormState({
    userId: firebaseUser?.uid, destination: '/create-game', initialForm, enabled: !isEditMode,
  })
  const initializedEditRef = useRef('')
  const [formBaseline, setFormBaseline] = useState(initialForm)
  const [currentUser, setCurrentUser] = useState(null)
  const [paymentMethod, setPaymentMethod] = useState(null)
  const [firstPublishIsFree, setFirstPublishIsFree] = useState(true)
  const [createdGameId, setCreatedGameId] = useState('')
  const [loadError, setLoadError] = useState('')
  const [isContextLoading, setIsContextLoading] = useState(false)
  const blockedVerificationRefreshRef = useRef('')

  useEffect(() => {
    let ignore = false

    async function loadVerifiedContext(effectiveAppUser) {
      // Saved cards and fee history are only for publishing a new game. Editing
      // charges no fee, and a suspended host, who may still edit, cannot load the
      // fee history.
      const [paymentMethods, gameContext, hostPublishFees] = await Promise.all([
        isEditMode ? Promise.resolve([]) : loadUserPaymentMethods(firebaseUser),
        isEditMode
          ? loadEditableGame(firebaseUser, gameId, effectiveAppUser.id)
          : Promise.resolve(null),
        isEditMode ? Promise.resolve([]) : loadHostPublishFees(firebaseUser),
      ])

      if (ignore) {
        return
      }

      setCurrentUser(effectiveAppUser)
      setPaymentMethod(paymentMethods.find((method) => method.is_default) || paymentMethods[0] || null)
      setFirstPublishIsFree(
        !hostPublishFees.some((fee) => fee.waiver_reason === 'first_game_free'),
      )

      const editKey = `${effectiveAppUser.id}:${gameId}`
      if (gameContext && initializedEditRef.current !== editKey) {
        const editableForm = mapGameToForm(
          gameContext.game,
          gameContext.venue,
          gameContext.communityDetails,
        )
        initializedEditRef.current = editKey
        setForm(editableForm)
        setFormBaseline(editableForm)
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
            setCreatedGameId('')
          }

          if (blockedVerificationRefreshRef.current !== appUser.id) {
            blockedVerificationRefreshRef.current = appUser.id
            refreshBlockedHost()
          }
          return
        }

        blockedVerificationRefreshRef.current = ''
        if (!ignore) {
          setIsContextLoading(true)
        }
        await loadVerifiedContext(appUser)
      } catch (error) {
        if (!ignore) {
          setLoadError(error instanceof Error ? error.message : 'Unable to load create game data.')
        }
      } finally {
        if (!ignore) {
          setIsContextLoading(false)
        }
      }
    }

    loadCreateGameContext()

    return () => {
      ignore = true
    }
  }, [
    appUser,
    firebaseUser,
    gameId,
    isEditMode,
    isLoading,
    onVerifiedHostRefresh,
    refreshCurrentUserVerification,
    setForm,
  ])

  return {
    createdGameId,
    currentUser,
    firstPublishIsFree,
    form,
    formBaseline,
    isContextLoading,
    loadError,
    paymentMethod,
    preserveForVerification,
    setCreatedGameId,
    setForm,
  }
}
