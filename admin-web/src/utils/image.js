// Serve uploaded files through the same proxy as the admin API.
export const formatImageUrl = (value) => {
  if (typeof value !== 'string' || !value.trim()) return ''
  const url = value.trim()
  if (/^(?:https?:\/\/tmp\/|wxfile:)/i.test(url)) return ''

  let pathname = url
  let suffix = ''
  if (/^(?:https?:)?\/\//i.test(url)) {
    try {
      const parsed = new URL(url, window.location.origin)
      pathname = parsed.pathname
      suffix = parsed.search + parsed.hash
    } catch {
      return ''
    }
  }

  if (/^\/?(?:api\/)?uploads\//.test(pathname)) {
    return '/api/uploads/' + pathname.replace(/^\/?(?:api\/)?uploads\//, '') + suffix
  }
  return url
}

export const formatImageList = (images) => {
  if (!Array.isArray(images)) return []
  return images.map(formatImageUrl).filter(Boolean)
}
