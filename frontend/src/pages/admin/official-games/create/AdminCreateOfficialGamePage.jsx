import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../../../hooks/useAuth.js'
import '../../../../styles/admin/AdminOfficialGames.css'
import '../../../../styles/admin/AdminOfficialGameCreate.css'
import AdminCreateOfficialGameLayout from './AdminCreateOfficialGameLayout.jsx'
import {
  buildAdminOfficialReplacementForm,
  initialAdminOfficialGameForm,
} from './adminCreateOfficialGameData.js'
import { buildAdminCreateOfficialGamePayload } from './adminCreateOfficialGamePayloads.js'
import {
  validateAdminOfficialCreateForm,
  validateAdminOfficialCreateStep,
} from './adminCreateOfficialGameValidation.js'
import {
  assertAdminVenueImageUploadsReady,
  createAdminOfficialGame,
  getAdminOfficialGame,
  uploadAdminVenueImage,
} from '../shared/adminOfficialGamesApi.js'

const MAX_VENUE_PHOTOS = 3
const MAX_VENUE_PHOTO_BYTES = 8 * 1024 * 1024
const ALLOWED_VENUE_PHOTO_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])

function createPhotoId(file) {
  const randomId = typeof globalThis.crypto?.randomUUID === 'function'
    ? globalThis.crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`

  return `${file.name}-${file.size}-${file.lastModified}-${randomId}`
}

function AdminCreateOfficialGameFlow() {
  const { currentUser } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const replacementSourceGameId = searchParams.get('replace_game_id') || ''
  const [activeStep, setActiveStep] = useState(1)
  const [createdGameId, setCreatedGameId] = useState('')
  const [form, setForm] = useState(initialAdminOfficialGameForm)
  const [replacementSourceGame, setReplacementSourceGame] = useState(null)
  const [replacementLoadState, setReplacementLoadState] = useState(
    replacementSourceGameId ? 'loading' : 'idle',
  )
  const [replacementLoadAttempt, setReplacementLoadAttempt] = useState(0)
  const [venuePhotos, setVenuePhotos] = useState([])
  const [saveState, setSaveState] = useState('idle')
  const [pageError, setPageError] = useState('')
  const [photoError, setPhotoError] = useState('')
  const [stepError, setStepError] = useState('')
  const venuePhotosRef = useRef(venuePhotos)

  useEffect(() => {
    venuePhotosRef.current = venuePhotos
  }, [venuePhotos])

  useEffect(
    () => () => {
      venuePhotosRef.current.forEach((photo) => URL.revokeObjectURL(photo.previewUrl))
    },
    [],
  )

  useEffect(() => {
    if (!currentUser || !replacementSourceGameId) {
      return undefined
    }

    let isMounted = true

    getAdminOfficialGame({
      firebaseUser: currentUser,
      gameId: replacementSourceGameId,
    })
      .then((response) => {
        if (!isMounted) {
          return
        }

        const sourceGame = response.game
        setReplacementSourceGame(sourceGame)
        setForm(buildAdminOfficialReplacementForm(sourceGame))
        setReplacementLoadState('ready')
        setPageError('')
      })
      .catch((error) => {
        if (!isMounted) {
          return
        }

        setReplacementSourceGame(null)
        setForm(initialAdminOfficialGameForm)
        setReplacementLoadState('error')
        setPageError(error.message || 'Replacement source game could not be loaded.')
      })

    return () => {
      isMounted = false
    }
  }, [currentUser, replacementLoadAttempt, replacementSourceGameId])

  function updateField(field, value) {
    if (replacementLoadState !== 'error') {
      setPageError('')
    }
    setStepError('')
    setForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }))
  }

  function retryReplacementSource() {
    setReplacementSourceGame(null)
    setReplacementLoadState('loading')
    setPageError('')
    setReplacementLoadAttempt((currentAttempt) => currentAttempt + 1)
  }

  function addVenuePhotos(files) {
    const selectedFiles = Array.from(files || [])
    if (selectedFiles.length === 0) {
      return
    }

    setPhotoError('')
    setVenuePhotos((currentPhotos) => {
      const remainingSlots = MAX_VENUE_PHOTOS - currentPhotos.length
      const nextFiles = selectedFiles.slice(0, Math.max(remainingSlots, 0))
      const rejectedFile = selectedFiles.find(
        (file, index) =>
          index >= remainingSlots ||
          !ALLOWED_VENUE_PHOTO_TYPES.has(file.type) ||
          file.size > MAX_VENUE_PHOTO_BYTES,
      )

      if (rejectedFile) {
        setPhotoError('Add up to 3 JPG, PNG, or WebP photos under 8 MB each.')
      }

      const validPhotos = nextFiles
        .filter((file) => ALLOWED_VENUE_PHOTO_TYPES.has(file.type))
        .filter((file) => file.size <= MAX_VENUE_PHOTO_BYTES)
        .map((file) => ({
          id: createPhotoId(file),
          file,
          name: file.name,
          previewUrl: URL.createObjectURL(file),
          size: file.size,
        }))

      return [...currentPhotos, ...validPhotos]
    })
  }

  function removeVenuePhoto(photoId) {
    setPhotoError('')
    setVenuePhotos((currentPhotos) => {
      const removedPhoto = currentPhotos.find((photo) => photo.id === photoId)
      if (removedPhoto) {
        URL.revokeObjectURL(removedPhoto.previewUrl)
      }

      return currentPhotos.filter((photo) => photo.id !== photoId)
    })
  }

  function goNext() {
    const error = validateAdminOfficialCreateStep(activeStep, form)
    if (error) {
      setStepError(error)
      return
    }

    setActiveStep((step) => Math.min(step + 1, 5))
  }

  function goBack() {
    setStepError('')
    setActiveStep((step) => Math.max(step - 1, 1))
  }

  function handleCancel() {
    navigate('/admin/official-games')
  }

  function openCreatedGame() {
    if (createdGameId) {
      navigate(`/admin/official-games/${createdGameId}`)
    }
  }

  async function uploadVenuePhotos(venueId) {
    if (venuePhotos.length === 0) {
      return
    }

    await Promise.all(
      venuePhotos.map((photo, index) =>
        uploadAdminVenueImage({
          file: photo.file,
          firebaseUser: currentUser,
          isPrimary: index === 0,
          sortOrder: index,
          venueId,
        }),
      ),
    )
  }

  async function handleCreateGame() {
    if (saveState === 'created') {
      openCreatedGame()
      return
    }

    if (
      replacementSourceGameId
      && (
        replacementLoadState !== 'ready'
        || replacementSourceGame?.id !== replacementSourceGameId
      )
    ) {
      setPageError('Load the replacement source game before creating its replacement.')
      return
    }

    const validationError = validateAdminOfficialCreateForm(form)
    if (validationError) {
      setActiveStep(validationError.step)
      setStepError(validationError.message)
      return
    }

    setSaveState('saving')
    setPageError('')
    setPhotoError('')
    let createdGame = null

    try {
      if (venuePhotos.length > 0) {
        setSaveState('checking_photos')
        await assertAdminVenueImageUploadsReady({ firebaseUser: currentUser })
      }

      setSaveState('saving')
      const response = await createAdminOfficialGame({
        firebaseUser: currentUser,
        payload: buildAdminCreateOfficialGamePayload(form, {
          replacementForGameId: replacementSourceGame?.id,
        }),
      })
      createdGame = response.game
      setCreatedGameId(createdGame.id)

      if (venuePhotos.length > 0) {
        setSaveState('uploading')
        await uploadVenuePhotos(createdGame.venue_id)
      }

      navigate('/admin/official-games')
    } catch (error) {
      if (createdGame?.id) {
        setPageError(error.message || 'Official game was created, but photos could not be uploaded.')
        setSaveState('created')
        return
      }

      setPageError(error.message || 'Official game could not be created.')
      setSaveState('idle')
    }
  }

  return (
    <AdminCreateOfficialGameLayout
      activeStep={activeStep}
      form={form}
      hasCreatedGame={Boolean(createdGameId)}
      pageError={pageError}
      photoError={photoError}
      photos={venuePhotos}
      replacementLoadState={replacementLoadState}
      replacementSourceGame={replacementSourceGame}
      saveState={saveState}
      stepError={stepError}
      onBack={goBack}
      onCancel={handleCancel}
      onCreate={handleCreateGame}
      onNext={goNext}
      onPhotoAdd={addVenuePhotos}
      onPhotoRemove={removeVenuePhoto}
      onRetryReplacementSource={retryReplacementSource}
      onUpdateField={updateField}
    />
  )
}

function AdminCreateOfficialGamePage() {
  const { search } = useLocation()

  return <AdminCreateOfficialGameFlow key={search} />
}

export default AdminCreateOfficialGamePage
