export const PAYMENT_ELEMENT_OPTIONS = {
  layout: {
    type: 'accordion',
    defaultCollapsed: false,
    radios: 'never',
  },
  paymentMethodOrder: ['card'],
  wallets: {
    applePay: 'never',
    googlePay: 'never',
    link: 'never',
  },
}

export function getRequestErrorMessage(error, fallbackMessage) {
  return error instanceof Error ? error.message : fallbackMessage
}

export function getSetupErrorMessage(error) {
  const message = getRequestErrorMessage(error, 'Unable to save this card.')
  if (message === 'This card is already saved.') {
    return 'This card is already saved. Enter a different card.'
  }

  return message
}

export function buildStripeElementsOptions(clientSecret) {
  return {
    clientSecret,
    appearance: {
      theme: 'night',
      variables: {
        colorPrimary: '#b8ff24',
        colorBackground: '#0c141d',
        colorText: '#f8fafc',
        colorDanger: '#ff6b73',
        borderRadius: '8px',
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      rules: {
        '.Input': {
          border: '1px solid rgba(248, 250, 252, 0.16)',
        },
        '.Tab': {
          border: '1px solid rgba(248, 250, 252, 0.16)',
        },
        '.Tab--selected': {
          borderColor: '#b8ff24',
          color: '#f8fafc',
        },
      },
    },
  }
}
