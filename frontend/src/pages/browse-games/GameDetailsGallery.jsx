export function GameGallery({
  activeImageIndex,
  images,
  onNext,
  onPrevious,
  onSelectImage,
}) {
  const activeImage = images[activeImageIndex]
  const hasMultipleImages = images.length > 1

  return (
    <section className="details-gallery" aria-label="Game photos">
      {activeImage ? (
        <img src={activeImage} alt="" />
      ) : (
        <div className="details-gallery__fallback">Pickup Lane</div>
      )}

      {hasMultipleImages && (
        <>
          <button
            className="details-gallery__arrow details-gallery__arrow--left"
            type="button"
            aria-label="Previous photo"
            onClick={onPrevious}
          >
            ‹
          </button>

          <button
            className="details-gallery__arrow details-gallery__arrow--right"
            type="button"
            aria-label="Next photo"
            onClick={onNext}
          >
            ›
          </button>

          <div className="details-gallery__dots" aria-label="Choose game photo">
            {images.map((image, index) => (
              <button
                className={index === activeImageIndex ? 'active' : ''}
                type="button"
                aria-label={`Show photo ${index + 1}`}
                onClick={() => onSelectImage(index)}
                key={`${image}-${index}`}
              />
            ))}
          </div>
        </>
      )}

      <span className="details-gallery__count">
        {Math.min(activeImageIndex + 1, Math.max(images.length, 1))} / {Math.max(images.length, 1)}
      </span>
    </section>
  )
}
