export const CHAT_LANGUAGE_KEY = 'masr-guide-reply-language-v1'
const LANGUAGES = new Set(['Arabic', 'English', 'French'])

export function restoreChatLanguage(messages, fallback = 'English') {
  try {
    const stored = sessionStorage.getItem(CHAT_LANGUAGE_KEY)
    if (LANGUAGES.has(stored)) return stored
  } catch { /* storage unavailable */ }
  return conversationLanguage(messages, fallback)
}

export function conversationLanguage(messages, fallback = 'English') {
  // Replay visitor turns so a short "ok" retains the preceding language.
  return messages.filter(m => m.role === 'user').reduce((language, m) =>
    inferChatLanguage(m.text || m.content || '', language), fallback)
}

// The chat follows the language used in this message; the site's language stays put.
export function inferChatLanguage(message, fallback = 'English') {
  const text = message.toLowerCase()
  if (/(?:speak|reply|respond|answer) (?:to me )?in arabic|باللغة العربية|بالعربي|ب العربي|خليها عربي|اتكلم عربي|تكلم عربي/.test(text)) return 'Arabic'
  if (/(?:speak|reply|respond|answer) (?:to me )?in english|بالإنجليزي|بالانجليزي/.test(text)) return 'English'
  if (/(?:speak|reply|respond|answer) (?:to me )?in french|بالفرنساوي|parlez en fran[çc]ais|en fran[çc]ais/.test(text)) return 'French'
  if (/\b(?:bonjour|bonsoir|salut|merci|parlez|français|francais|comment aller|louxor|assouan|je vais|je voudrais|pouvez-vous|peux-tu|avec mes enfants|pour cinq jours|dix jours|pendant \w+ jours)\b/.test(text)) return 'French'
  const arabic = (text.match(/[\u0621-\u064a]/g) || []).length
  const latin = (text.match(/[a-z]/g) || []).length
  if (arabic && latin) return arabic >= latin ? 'Arabic' : 'English'
  if (arabic) return 'Arabic'
  if (latin) {
    const words = text.match(/[a-z]+/g) || []
    if (words.length === 1 && new Set(['ok', 'okay', 'yes', 'no', 'cairo', 'giza', 'luxor', 'aswan', 'hurghada', 'dahab', 'alexandria']).has(words[0])) return fallback
    return 'English'
  }
  return fallback
}
