import { Link } from 'react-router-dom'
import {
  MapPinIcon,
  PencilIcon,
} from '../../components/BrowseIcons.jsx'
import { GameChatCard } from './GameDetailsChat.jsx'
import { GameGallery } from './GameDetailsGallery.jsx'
import { HostPaymentSection } from './GameDetailsHostPayment.jsx'
import { WhereToGoCard } from './GameDetailsLocation.jsx'
import GameDetailsMobileActions from './GameDetailsMobileActions.jsx'
import { PlayersCard } from './GameDetailsPlayers.jsx'
import { QuickFacts } from './GameDetailsQuickFacts.jsx'
import { BookingRulesCard } from './GameDetailsRules.jsx'
import { StatusPill } from './GameDetailsScaffold.jsx'

export function GameDetailsMainColumn({
  aboutText,
  activeImageIndex,
  canCancelGame,
  canEditGame,
  canOpenGameChat,
  canShowCancelGame,
  canShowEditGame,
  chatMessages,
  chatSenderNames,
  currentGuestCount,
  currentParticipant,
  currentUser,
  facts,
  game,
  gameToneLabel,
  hasUnreadChat,
  heroLocation,
  hostGuestMax,
  hostPaymentMethods,
  images,
  isAddingHostGuest,
  isCancelledGame,
  isCancellingGame,
  isHost,
  isJoinWindowClosed,
  isUpdatingGuests,
  latestChatMessage,
  mapsUrl,
  mobileActionCount,
  onNextImage,
  onOpenCancelGameModal,
  onOpenChat,
  onOpenHostGuestModal,
  onOpenLeaveModal,
  onOpenPlayerList,
  onPreviousImage,
  onSelectImage,
  onShare,
  parkingNote,
  participantSummary,
  price,
  ruleItems,
  shareCopied,
  title,
  venueAddress,
  venueName,
}) {
  return (
    <div className="details-main">
      <div className="details-titlebar">
        <Link className="details-back-to-browse" to="/games">
          ← Back
        </Link>

        <StatusPill label={gameToneLabel} />
      </div>

      <div className="details-heading">
        <h1>{title}</h1>
        <p>
          <MapPinIcon />
          {heroLocation}
        </p>
      </div>

      <GameGallery
        activeImageIndex={activeImageIndex}
        images={images}
        onNext={onNextImage}
        onPrevious={onPreviousImage}
        onSelect={onSelectImage}
      />

      <QuickFacts facts={facts} price={price} variant="desktop" />

      <section className="details-mobile-summary">
        <div className="details-mobile-summary__meta">
          <StatusPill label={gameToneLabel} />
        </div>

        <h1>{title}</h1>

        <p>
          <MapPinIcon />
          {heroLocation}
        </p>

        <QuickFacts facts={facts} price={price} variant="mobile" />
      </section>

      <GameDetailsMobileActions
        canCancelGame={canCancelGame}
        canEditGame={canEditGame}
        canShowCancelGame={canShowCancelGame}
        canShowEditGame={canShowEditGame}
        currentGuestCount={currentGuestCount}
        currentParticipant={currentParticipant}
        gameId={game.id}
        hostGuestMax={hostGuestMax}
        isAddingHostGuest={isAddingHostGuest}
        isCancellingGame={isCancellingGame}
        isHost={isHost}
        isJoinWindowClosed={isJoinWindowClosed}
        isUpdatingGuests={isUpdatingGuests}
        mobileActionCount={mobileActionCount}
        onOpenCancelGameModal={onOpenCancelGameModal}
        onOpenHostGuestModal={onOpenHostGuestModal}
        onOpenLeaveModal={onOpenLeaveModal}
        onShare={onShare}
        shareCopied={shareCopied}
        shareDisabled={isCancelledGame}
      />

      {!currentUser?.id && !isCancelledGame && (
        <section className="details-member-access-notice">
          <p>
            <Link state={{ from: `/games/${game.id}` }} to="/create-account">
              Create an Account
            </Link>{' '}
            or{' '}
            <Link state={{ from: `/games/${game.id}` }} to="/sign-in">
              Sign In
            </Link>{' '}
            to view the player list and use game chat.
          </p>
        </section>
      )}

      <section className="details-card details-mobile-info-section details-mobile-about-section">
        <h2 className="details-section-heading">
          <span className="details-section-icon">
            <PencilIcon />
          </span>
          About This Game
        </h2>
        <p>{aboutText}</p>

        {hostPaymentMethods.length > 0 && (
          <HostPaymentSection methods={hostPaymentMethods} />
        )}
      </section>

      <section className="details-card-grid">
        <PlayersCard
          cta="View player list"
          ctaDisabled={!currentUser?.id}
          onOpenPlayerList={currentUser?.id ? onOpenPlayerList : undefined}
          participantSummary={participantSummary}
        />

        <GameChatCard
          canOpenChat={canOpenGameChat}
          hasUnread={hasUnreadChat}
          latestChatMessage={latestChatMessage}
          messageCount={chatMessages.length}
          onOpenChat={onOpenChat}
          senderNames={chatSenderNames}
        />
      </section>

      <BookingRulesCard policyUrl="/policies/cancellation-refunds" rules={ruleItems} />

      <WhereToGoCard
        address={venueAddress}
        mapIcon={<MapPinIcon />}
        mapsUrl={mapsUrl}
        parkingNote={parkingNote}
        venueName={venueName}
      />

      <section className="details-card details-mobile-info-section">
        <h2>Questions?</h2>
        <p>Check out our Help Center or contact our support team.</p>
        <a className="details-help-button" href="mailto:support@pickuplane.local">
          Visit Help Center
        </a>
      </section>
    </div>
  )
}
