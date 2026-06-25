import { useRef } from 'react'
import { MapPinIcon, PlusCircleIcon } from '../../../../components/BrowseIcons.jsx'
import { FormErrorMessage } from '../../../../components/FormErrorMessage.jsx'
import {
  AdminCreateSelectInput,
  AdminCreateStepHeading,
  AdminCreateTextarea,
  AdminCreateTextInput,
} from './AdminCreateOfficialGameControls.jsx'
import {
  adminOfficialCreateFieldLimits,
  US_STATE_OPTIONS,
} from './adminCreateOfficialGameData.js'

function AdminCreateOfficialGameVenueStep({
  form,
  onPhotoAdd,
  onPhotoRemove,
  photoError,
  photos,
  updateField,
}) {
  const photoInputRef = useRef(null)
  const canAddPhotos = photos.length < 3

  function openPhotoPicker() {
    photoInputRef.current?.click()
  }

  function handlePhotoChange(event) {
    onPhotoAdd(event.target.files)
    event.target.value = ''
  }

  return (
    <>
      <AdminCreateStepHeading
        title="Where will you play?"
        text="Add the venue details players will see on the official game page."
      />

      <div className="admin-create-location-fields">
        <div className="admin-create-location-field admin-create-location-field--venue">
          <AdminCreateTextInput
            field="venueName"
            form={form}
            label="Venue name"
            maxLength={adminOfficialCreateFieldLimits.venueName}
            updateField={updateField}
          />
        </div>
        <div className="admin-create-location-field admin-create-location-field--street">
          <AdminCreateTextInput
            field="addressLine1"
            form={form}
            label="Street address"
            maxLength={adminOfficialCreateFieldLimits.addressLine1}
            updateField={updateField}
          />
        </div>
        <div className="admin-create-location-field admin-create-location-field--city">
          <AdminCreateTextInput
            field="city"
            form={form}
            label="City"
            maxLength={adminOfficialCreateFieldLimits.city}
            updateField={updateField}
          />
        </div>
        <div className="admin-create-location-field admin-create-location-field--state">
          <AdminCreateSelectInput
            field="state"
            form={form}
            label="State"
            options={US_STATE_OPTIONS}
            updateField={updateField}
          />
        </div>
        <div className="admin-create-location-field admin-create-location-field--zip">
          <AdminCreateTextInput
            field="postalCode"
            form={form}
            label="ZIP code"
            maxLength={adminOfficialCreateFieldLimits.postalCode}
            updateField={updateField}
          />
        </div>
        <div className="admin-create-location-field admin-create-location-field--neighborhood">
          <AdminCreateTextInput
            field="neighborhood"
            form={form}
            label="Neighborhood (optional)"
            maxLength={adminOfficialCreateFieldLimits.neighborhood}
            updateField={updateField}
          />
        </div>
      </div>

      <div className="admin-create-location-note">
        <AdminCreateTextarea
          field="parkingNotes"
          form={form}
          label="Parking note (optional)"
          maxLength={adminOfficialCreateFieldLimits.parkingNotes}
          placeholder="Share parking info or nearby options."
          updateField={updateField}
        />
      </div>

      <div className="admin-create-photo-panel" aria-label="Venue photos">
        <div>
          <MapPinIcon />
          <div>
            <h3>Venue photos</h3>
            <p>{photos.length ? `${photos.length}/3 selected` : 'No venue photos added yet.'}</p>
          </div>
        </div>
        <button type="button" disabled={!canAddPhotos} onClick={openPhotoPicker}>
          <PlusCircleIcon />
          Add photos
        </button>
        <input
          ref={photoInputRef}
          accept="image/jpeg,image/png,image/webp"
          className="admin-create-photo-input"
          multiple
          type="file"
          onChange={handlePhotoChange}
        />
      </div>

      <FormErrorMessage>{photoError}</FormErrorMessage>

      {photos.length > 0 && (
        <div className="admin-create-photo-grid" aria-label="Selected venue photos">
          {photos.map((photo, index) => (
            <figure className="admin-create-photo-thumb" key={photo.id}>
              <img src={photo.previewUrl} alt="" />
              <figcaption>
                <span>{index === 0 ? 'Primary' : `Gallery ${index}`}</span>
                <button
                  className="admin-create-photo-remove"
                  type="button"
                  aria-label={`Remove ${index === 0 ? 'primary photo' : `gallery photo ${index}`}`}
                  title="Remove photo"
                  onClick={() => onPhotoRemove(photo.id)}
                >
                  <span aria-hidden="true" />
                </button>
              </figcaption>
            </figure>
          ))}
        </div>
      )}
    </>
  )
}

export default AdminCreateOfficialGameVenueStep
