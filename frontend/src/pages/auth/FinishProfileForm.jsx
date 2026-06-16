import { ArrowRight } from 'lucide-react'
import { InfoIcon, UserIcon } from '../../components/AuthIcons.jsx'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import { AuthField } from '../../features/auth/AuthFields.jsx'
import { BirthdayField } from '../../features/auth/BirthdayField.jsx'

export function FinishProfileForm({
  birthDay,
  birthMonth,
  birthYear,
  error,
  firstName,
  isDisabled,
  isSubmitting,
  lastName,
  onSubmit,
  setBirthDay,
  setBirthMonth,
  setBirthYear,
  setFirstName,
  setLastName,
}) {
  return (
    <form autoComplete="off" className="auth-form" onSubmit={onSubmit}>
      <div className="auth-two-column">
        <AuthField
          autoComplete="off"
          disabled={isDisabled}
          icon={<UserIcon />}
          label="First Name"
          onChange={(event) => setFirstName(event.target.value)}
          placeholder="First name"
          required
          value={firstName}
        />
        <AuthField
          autoComplete="off"
          disabled={isDisabled}
          icon={<UserIcon />}
          label="Last Name"
          onChange={(event) => setLastName(event.target.value)}
          placeholder="Last name"
          required
          value={lastName}
        />
      </div>

      <BirthdayField
        day={birthDay}
        disabled={isDisabled}
        month={birthMonth}
        onDayChange={setBirthDay}
        onMonthChange={setBirthMonth}
        onYearChange={setBirthYear}
        year={birthYear}
      />

      <p className="auth-inline-note">
        <InfoIcon />
        You must be at least 13 years old to use Pickup Lane.
      </p>

      <FormErrorMessage>{error}</FormErrorMessage>

      <button
        className="auth-primary-button"
        disabled={isDisabled}
        type="submit"
      >
        <ArrowRight aria-hidden="true" />
        {isSubmitting ? 'Saving...' : 'Continue'}
      </button>
    </form>
  )
}
