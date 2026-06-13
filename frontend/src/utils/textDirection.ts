/* Automatic text-direction detection for Arabic / English content */

const ARABIC_RANGE = /[\u0600-\u06FF]/

/**
 * Returns true when the text contains ANY Arabic Unicode character.
 * Punctuation and whitespace are irrelevant — a single Arabic letter is enough.
 */
export function hasArabic(text: string): boolean {
  return ARABIC_RANGE.test(text)
}

/** Returns the best-fit writing direction for a given piece of text. */
export function getTextDirection(text: string): 'rtl' | 'ltr' {
  return hasArabic(text) ? 'rtl' : 'ltr'
}
