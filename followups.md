# Followups

- Remove the demo payment blockers before enabling paid official game checkout publicly. Re-enable only after Stripe config, webhook handling, checkout UX, and saved-card flows are verified end to end; the current flags are `ENABLE_STRIPE_PAYMENTS=true` for the backend and `VITE_ENABLE_STRIPE_PAYMENTS=true` for the frontend.
