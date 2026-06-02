import { useState, useCallback, useEffect } from 'react'

const DEFAULT_FILTERS = {
  region:  'All',
  topic:   'All',
  source:  'All',
  keyword: '',
}

function readFromURL() {
  const params = new URLSearchParams(window.location.search)
  return {
    region:  params.get('region')  || 'All',
    topic:   params.get('topic')   || 'All',
    source:  params.get('source')  || 'All',
    keyword: params.get('keyword') || '',
  }
}

function writeToURL(filters) {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, val]) => {
    if (val && val !== 'All' && val !== '') {
      params.set(key, val)
    }
  })
  const search = params.toString()
  const newUrl = search
    ? `${window.location.pathname}?${search}`
    : window.location.pathname
  window.history.replaceState(null, '', newUrl)
}

export function useFilters() {
  const [filters, setFilters] = useState(() => readFromURL())

  // Sync to URL whenever filters change
  useEffect(() => {
    writeToURL(filters)
  }, [filters])

  const setRegion = useCallback((region) =>
    setFilters(f => ({ ...f, region })), [])

  const setTopic = useCallback((topic) =>
    setFilters(f => ({ ...f, topic })), [])

  const setSource = useCallback((source) =>
    setFilters(f => ({ ...f, source })), [])

  const setKeyword = useCallback((keyword) =>
    setFilters(f => ({ ...f, keyword })), [])

  const resetFilters = useCallback(() =>
    setFilters(DEFAULT_FILTERS), [])

  return {
    filters,
    setRegion,
    setTopic,
    setSource,
    setKeyword,
    resetFilters,
  }
}
