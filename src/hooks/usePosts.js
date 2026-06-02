import { useState, useEffect, useRef } from 'react'
import { supabase } from '../lib/supabase'

export function usePosts(filters) {
  const [posts,   setPosts]   = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  // Debounce keyword to avoid query-per-keystroke
  const [debouncedKeyword, setDebouncedKeyword] = useState(filters.keyword)
  const debounceTimer = useRef(null)

  useEffect(() => {
    clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(() => {
      setDebouncedKeyword(filters.keyword)
    }, 300)
    return () => clearTimeout(debounceTimer.current)
  }, [filters.keyword])

  useEffect(() => {
    let cancelled = false

    async function fetchPosts() {
      setLoading(true)
      setError(null)

      try {
        let q = supabase
          .from('linkedin_posts')
          .select('*')
          .order('published_at', { ascending: false })
          // Hide rows the AI marked as having no substantive content
          // (ai_headline = '' is the "processed but skipped" marker).
          // NULL is fine — those just haven't been AI-processed yet.
          .or('ai_headline.is.null,ai_headline.neq.')

        // ── Region filter ──────────────────────────────────────────────
        // Categories in DB are "{Region} | {EntityType}", e.g. "UAE | Insurer".
        // UAE and GCC match by prefix; International = everything else (Europe,
        // Americas, Africa, South Asia, Global).
        const { region } = filters
        if (region === 'UAE' || region === 'GCC') {
          q = q.like('category', `${region} | %`)
        } else if (region === 'International') {
          q = q.not('category', 'like', 'UAE | %')
               .not('category', 'like', 'GCC | %')
        }

        // ── Topic filter ───────────────────────────────────────────────
        if (filters.topic !== 'All') {
          q = q.eq('topic', filters.topic)
        }

        // ── Source filter ──────────────────────────────────────────────
        if (filters.source !== 'All') {
          q = q.eq('source', filters.source)
        }

        // ── Keyword search across headline and summary ─────────────────
        if (debouncedKeyword.trim()) {
          const kw = debouncedKeyword.trim()
          q = q.or(
            `ai_headline.ilike.%${kw}%,ai_summary.ilike.%${kw}%,title.ilike.%${kw}%`
          )
        }

        const { data, error: sbError } = await q

        if (cancelled) return
        if (sbError) throw sbError
        setPosts(data || [])
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load posts')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchPosts()
    return () => { cancelled = true }
  }, [filters.region, filters.topic, filters.source, debouncedKeyword])

  return { posts, loading, error }
}
