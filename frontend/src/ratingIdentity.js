export function ratingVisitorId() {
  let id = localStorage.getItem('masr-guide-rating-visitor-id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('masr-guide-rating-visitor-id', id)
  }
  return id
}
