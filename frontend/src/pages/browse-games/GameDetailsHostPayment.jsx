export function HostPaymentSection({ methods }) {
  if (!methods.length) {
    return null
  }

  return (
    <div className="details-host-payment-section">
      <div className="details-host-payment-list">
        {methods.map((method, index) => (
          <div className="details-host-payment-row" key={`${method.type}-${method.value}-${index}`}>
            <strong>{formatPaymentMethodType(method.type)}</strong>
            <span>{method.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function formatPaymentMethodType(type) {
  const normalizedType = String(type || '').trim().toLowerCase()

  if (normalizedType === 'venmo') {
    return 'Venmo'
  }

  if (normalizedType === 'zelle') {
    return 'Zelle'
  }

  if (normalizedType === 'cashapp') {
    return 'Cash App'
  }

  if (normalizedType === 'cash') {
    return 'Cash'
  }

  return normalizedType ? normalizedType.replace(/^\w/, (letter) => letter.toUpperCase()) : 'Payment'
}
