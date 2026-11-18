import { useEffect, useState } from 'react'
import { loadGameCheckoutQuote } from './gameCheckoutApi.js'

// Loads the amount due after credit whenever the proposed party changes.
export function useGameCheckoutQuote({ addGuests, enabled, firebaseUser, gameId, guestCount }) {
  const [result, setResult] = useState({ key: '', quote: null, error: '' })
  const requestKey = enabled ? `${gameId}:${guestCount}:${addGuests}` : ''

  useEffect(() => {
    if (!requestKey) {
      return undefined
    }

    let ignore = false

    loadGameCheckoutQuote({ addGuests, firebaseUser, gameId, guestCount })
      .then((quote) => {
        if (!ignore) {
          setResult({ key: requestKey, quote, error: '' })
        }
      })
      .catch((requestError) => {
        if (!ignore) {
          setResult({
            key: requestKey,
            quote: null,
            error: requestError instanceof Error ? requestError.message : 'Unable to load the price.',
          })
        }
      })

    return () => {
      ignore = true
    }
  }, [addGuests, firebaseUser, gameId, guestCount, requestKey])

  if (!requestKey) {
    return { quote: null, quoteError: '', quoteStatus: 'idle' }
  }

  if (result.key !== requestKey) {
    return { quote: null, quoteError: '', quoteStatus: 'loading' }
  }

  return {
    quote: result.quote,
    quoteError: result.error,
    quoteStatus: result.error ? 'error' : 'success',
  }
}
