/** Customer-facing browser guard; the backend rechecks untrusted requests. */
const CARD_PATTERN = /(?:^|[^\d])(?:\d[ -]?){13,19}(?!\d)/
const CARD_PATTERN_GLOBAL = /(?:^|[^\d])(?:\d[ -]?){13,19}(?!\d)/g
export const likelyPaymentNumber = value => CARD_PATTERN.test(String(value))
export const scrubPaymentNumber = value => String(value).replace(CARD_PATTERN_GLOBAL,
  match => match.replace(/(?:\d[ -]?){13,19}/, '[payment number redacted]'))
