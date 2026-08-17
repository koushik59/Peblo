import React, { useRef, useState, useEffect } from 'react';
import { Show } from '../api';

const API_BASE = '/api';

interface Props {
  title: string;
  shows: Show[];
  onSelectShow: (show: Show) => void;
}

export default function SectionRow({ title, shows, onSelectShow }: Props) {
  const rowRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const checkScrollability = () => {
    if (rowRef.current) {
      const { scrollLeft, scrollWidth, clientWidth } = rowRef.current;
      setCanScrollLeft(scrollLeft > 10);
      setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 10);
    }
  };

  useEffect(() => {
    checkScrollability();
    window.addEventListener('resize', checkScrollability);
    return () => window.removeEventListener('resize', checkScrollability);
  }, [shows]);

  const scroll = (direction: 'left' | 'right') => {
    if (rowRef.current) {
      const scrollAmount = rowRef.current.clientWidth * 0.75;
      rowRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      });
      setTimeout(checkScrollability, 350);
    }
  };

  if (shows.length === 0) return null;

  return (
    <div className="section-row-carousel">
      <div className="section-header-row">
        <h2 className="section-title">
          <span className="section-accent-line" />
          <span>{title}</span>
          <span className="section-count">({shows.length})</span>
        </h2>
      </div>

      <div className="row-carousel-container">
        {/* Left Arrow */}
        <button
          className={`row-arrow row-arrow-left ${canScrollLeft ? 'visible' : ''}`}
          onClick={() => scroll('left')}
          aria-label={`Scroll left in ${title}`}
        >
          ‹
        </button>

        {/* Scrollable Track */}
        <div
          className="row-scroll-track"
          ref={rowRef}
          onScroll={checkScrollability}
        >
          {shows.map((show) => {
            const seasonCount = (show.seasons || []).filter((s) => s.number !== 0).length;
            return (
              <div
                key={show.id}
                className="carousel-poster-card"
                onClick={() => onSelectShow(show)}
              >
                <div className="card-media-wrapper">
                  {show.poster ? (
                    <img
                      src={`${API_BASE}${show.poster}`}
                      alt={show.title}
                      loading="lazy"
                    />
                  ) : (
                    <div className="poster-placeholder">
                      <span className="placeholder-icon">🎬</span>
                      <span className="placeholder-title">{show.title}</span>
                    </div>
                  )}
                  <div className="card-play-overlay">
                    <div className="play-circle">▶</div>
                  </div>
                </div>

                <div className="card-info-footer">
                  <div className="card-title-text" title={show.title}>
                    {show.title}
                  </div>
                  <div className="card-meta-row">
                    {show.category && <span className="meta-category-badge">{show.category}</span>}
                    {seasonCount > 0 && (
                      <span className="meta-seasons-badge">
                        {seasonCount} {seasonCount === 1 ? 'Season' : 'Seasons'}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Arrow */}
        <button
          className={`row-arrow row-arrow-right ${canScrollRight ? 'visible' : ''}`}
          onClick={() => scroll('right')}
          aria-label={`Scroll right in ${title}`}
        >
          ›
        </button>
      </div>
    </div>
  );
}
