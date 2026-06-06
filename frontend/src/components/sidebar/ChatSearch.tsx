import React, { useState, useEffect } from 'react'
import './ChatSearch.css'

interface ChatSearchProps {
  searchQuery: string
  onSearchChange: (query: string) => void
  placeholder?: string
}

export function ChatSearch({ 
  searchQuery,
  onSearchChange,
  placeholder = "Search conversations..." 
}: ChatSearchProps) {
  const [localQuery, setLocalQuery] = useState(searchQuery)

  // Sync local state with external search query
  useEffect(() => {
    setLocalQuery(searchQuery)
  }, [searchQuery])

  // Debounce the search query
  useEffect(() => {
    const timer = setTimeout(() => {
      onSearchChange(localQuery)
    }, 200)

    return () => {
      clearTimeout(timer)
    }
  }, [localQuery, onSearchChange])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalQuery(e.target.value)
  }

  return (
    <div className="chat-search">
      <input
        type="text"
        placeholder={placeholder}
        value={localQuery}
        onChange={handleInputChange}
        className="search-input"
        aria-label="Search conversations"
      />
    </div>
  )
}