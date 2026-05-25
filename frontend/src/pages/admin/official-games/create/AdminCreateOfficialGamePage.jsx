import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../../../hooks/useAuth.js'
import '../../../../styles/admin/AdminOfficialGames.css'
import '../../../../styles/admin/AdminOfficialGameCreate.css'
import AdminCreateOfficialGameLayout from './AdminCreateOfficialGameLayout.jsx'
import { initialAdminOfficialGameForm } from './adminCreateOfficialGameData.js'
import { buildAdminCreateOfficialGamePayload } from './adminCreateOfficialGamePayloads.js'
import {
  validateAdminOfficialCreateForm,
  validateAdminOfficialCreateStep,
} from './adminCreateOfficialGameValidation.js'
import {
  assertAdminVenueImageUploadsReady,
  createAdminOfficialGame,
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

function AdminCreateOfficialGamePage() {
  const { currentUser } = useAuth()
  const navigate = useNavigate()
  const [activeStep, setActiveStep] = useState(1)
  const [createdGameId, setCreatedGameId] = useState('')
  const [form, setForm] = useState(initialAdminOfficialGameForm)
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

  function updateField(field, value) {
    setPageError('')
    setStepError('')
    setForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }))
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
        payload: buildAdminCreateOfficialGamePayload(form),
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
      saveState={saveState}
      stepError={stepError}
      onBack={goBack}
      onCancel={handleCancel}
      onCreate={handleCreateGame}
      onNext={goNext}
      onPhotoAdd={addVenuePhotos}
      onPhotoRemove={removeVenuePhoto}
      onUpdateField={updateField}
    />
  )
}

export default AdminCreateOfficialGamePage
