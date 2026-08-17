import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { searchCatalog, Show, SearchResult } from '../api';
import ShowDetailModal from '../components/ShowDetailModal';

const API_BASE = '/api';

const QUICK_SEARCH_CHIPS = [
  'All',
  'Adventure',
  'India',
  'Learning',
  'Music',
  'Stories',
  'Nature',
  'Science',
  'Singalong',
];

const CATEGORIES = [
  '',
  'adventure',
  'folk',
  'friendship',
  'india',
  'language',
  'learning',
  'maths',
  'music',
  'nature',
  'reading',
  'science',
  'singalong',
  'stories',
  'travel',
  'values',
];

const LANGUAGES = [
  { code: '', label: 'All Languages' },
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'Hindi' },
  { code: 'ta', label: 'Tamil' },
  { code: 'te', label: 'Telugu' },
  { code: 'kn', label: 'Kannada' },
];

const SECTIONS = ['', 'featured', 'series', 'minisodes', 'songs'];

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [language, setLanguage] = useState('');
  const [section, setSection] = useState('');
  const [selectedShow, setSelectedShow] = useState<Show | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['catalog-search', query, category, language, section],
    queryFn: () =>
      searchCatalog({
        q: query || undefined,
        category: category || undefined,
        language: language || undefined,
        section: section || undefined,
      }),
  });

  const results: SearchResult[] = data?.results || [];

  const handleChipClick = (chip: string) => {
    if (chip === 'All') {
      setCategory('');
      setQuery('');
    } else {
      setCategory(chip.toLowerCase());
    }
  };

  return (
    <div className="hotstar-search-container">
      {/* Top Search Bar (JioHotstar Style) */}
      <div className="hotstar-search-bar-wrap">
        <div className="hotstar-search-input-box">
          <span className="search-icon-svg">🔍</span>
          <input
            id="viewer-search-input"
            type="text"
            placeholder="Movies, shows and more"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
          {query && (
            <button
              className="search-clear-btn"
              onClick={() => setQuery('')}
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        {/* Quick Tag Chips & Filters */}
        <div className="hotstar-filter-strip">
          {/* Quick Clickable Category Chips */}
          <div className="hotstar-chips-row">
            {QUICK_SEARCH_CHIPS.map((chip) => {
              const isActive =
                (chip === 'All' && !category && !query) ||
                category.toLowerCase() === chip.toLowerCase();
              return (
                <button
                  key={chip}
                  className={`hotstar-chip ${isActive ? 'active' : ''}`}
                  onClick={() => handleChipClick(chip)}
                >
                  {chip}
                </button>
              );
            })}
          </div>

          {/* Advanced Dropdown Selectors */}
          <div className="hotstar-select-row">
            <select
              id="filter-category-select"
              className="hotstar-select"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="">All Categories</option>
              {CATEGORIES.filter(Boolean).map((cat) => (
                <option key={cat} value={cat}>
                  {cat.charAt(0).toUpperCase() + cat.slice(1)}
                </option>
              ))}
            </select>

            <select
              id="filter-language-select"
              className="hotstar-select"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              {LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.label}
                </option>
              ))}
            </select>

            <select
              id="filter-section-select"
              className="hotstar-select"
              value={section}
              onChange={(e) => setSection(e.target.value)}
            >
              <option value="">All Sections</option>
              {SECTIONS.filter(Boolean).map((sec) => (
                <option key={sec} value={sec}>
                  {sec.charAt(0).toUpperCase() + sec.slice(1)}
                </option>
              ))}
            </select>

            {(query || category || language || section) && (
              <button
                className="hotstar-reset-btn"
                onClick={() => {
                  setQuery('');
                  setCategory('');
                  setLanguage('');
                  setSection('');
                }}
              >
                Reset All
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="loading-spinner">
          <div className="spinner-circle" />
          <div>Searching content...</div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="empty-state">
          <h3>Search unavailable</h3>
          <p>Failed to query the catalog. Please try again.</p>
        </div>
      )}

      {/* Results Grid (JioHotstar Style) */}
      {!isLoading && !error && (
        <div className="hotstar-search-results-section">
          <div className="results-header-row">
            <h2 className="results-heading">
              {query || category || language || section
                ? `Search Results (${results.length})`
                : 'Popular Searches'}
            </h2>
          </div>

          {results.length === 0 ? (
            <div className="empty-state">
              <h3>No matching shows found</h3>
              <p>Try searching for a different title, character, or category.</p>
            </div>
          ) : (
            <div className="hotstar-poster-grid">
              {results.map(({ show, section: secName }, idx) => {
                const regularSeasons = (show.seasons || []).filter((s) => s.number !== 0);
                const badgeLabel =
                  idx % 3 === 0
                    ? 'NEW RELEASE'
                    : idx % 3 === 1
                    ? 'POPULAR'
                    : 'TOP RATED';

                return (
                  <div
                    key={`${secName}-${show.id}`}
                    className="hotstar-grid-card"
                    onClick={() => setSelectedShow(show)}
                  >
                    <div className="grid-card-media">
                      {show.poster ? (
                        <img
                          src={`${API_BASE}${show.poster}`}
                          alt={show.title}
                          loading="lazy"
                        />
                      ) : (
                        <div className="grid-card-fallback">
                          <span className="fallback-emoji">🎬</span>
                          <span className="fallback-title">{show.title}</span>
                        </div>
                      )}

                      {/* Hotstar Ribbon Badge */}
                      <div className="card-hotstar-badge">{badgeLabel}</div>

                      {/* Hover Play Overlay */}
                      <div className="card-hover-overlay">
                        <div className="hover-play-btn">▶</div>
                      </div>
                    </div>

                    <div className="grid-card-footer">
                      <div className="grid-card-title" title={show.title}>
                        {show.title}
                      </div>
                      <div className="grid-card-meta">
                        {show.category && (
                          <span className="grid-meta-tag">{show.category}</span>
                        )}
                        {regularSeasons.length > 0 && (
                          <span className="grid-meta-season">
                            {regularSeasons.length}S
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Show Detail Modal */}
      {selectedShow && (
        <ShowDetailModal show={selectedShow} onClose={() => setSelectedShow(null)} />
      )}
    </div>
  );
}
