import React, { useState, useEffect, useRef } from 'react';
import { Show } from '../api';

const API_BASE = '/api';
const SLIDE_DURATION = 6000; // 6 seconds per slide

interface Props {
  shows: Show[];
  onSelectShow: (show: Show) => void;
  isModalOpen: boolean;
}

export default function HeroCarousel({ shows, onSelectShow, isModalOpen }: Props) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isHovered, setIsHovered] = useState(false);
  const timerRef = useRef<number | null>(null);
  const thumbListRef = useRef<HTMLDivElement | null>(null);

  const carouselShows = shows.length > 0 ? shows.slice(0, 8) : [];

  const nextSlide = () => {
    setCurrentIndex((prev) => (prev + 1) % carouselShows.length);
  };

  const prevSlide = () => {
    setCurrentIndex((prev) => (prev - 1 + carouselShows.length) % carouselShows.length);
  };

  const goToSlide = (index: number) => {
    setCurrentIndex(index);
  };

  // Auto-advance timer (pauses when hovered or modal is open)
  useEffect(() => {
    if (carouselShows.length <= 1 || isHovered || isModalOpen) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    timerRef.current = window.setInterval(() => {
      nextSlide();
    }, SLIDE_DURATION);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [currentIndex, carouselShows.length, isHovered, isModalOpen]);

  // Keep active thumbnail in view
  useEffect(() => {
    const container = thumbListRef.current;
    if (container) {
      const activeEl = container.children[currentIndex] as HTMLElement;
      if (activeEl) {
        const leftOffset = activeEl.offsetLeft - container.offsetLeft;
        container.scrollTo({ left: Math.max(0, leftOffset - 40), behavior: 'smooth' });
      }
    }
  }, [currentIndex]);

  if (carouselShows.length === 0) return null;

  const currentShow = carouselShows[currentIndex];
  const regularSeasons = (currentShow.seasons || []).filter((s) => s.number !== 0);
  const totalEpisodes = (currentShow.seasons || []).reduce((acc, s) => acc + (s.episodes?.length || 0), 0);

  // Extract available languages
  const availableLangs = Array.from(
    new Set(
      (currentShow.seasons || []).flatMap((s) =>
        (s.episodes || []).flatMap((e) => e.languages || [])
      )
    )
  );

  // Generate genre tags like JioHotstar (Category | Highlights)
  const genres = [
    currentShow.category ? currentShow.category.toUpperCase() : 'ENTERTAINMENT',
    regularSeasons.length > 0 ? 'ORIGINALS' : 'EXCLUSIVE',
    'FAMILY',
    'TOP RATED',
  ].filter(Boolean);

  return (
    <div
      className="hotstar-hero-container"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Background Cinematic Artwork Layers */}
      <div className="hotstar-backdrop-wrapper">
        {carouselShows.map((show, idx) => {
          const isActive = idx === currentIndex;
          return (
            <div
              key={show.id || idx}
              className={`hotstar-backdrop-slide ${isActive ? 'active' : ''}`}
              style={{
                backgroundImage: show.banner ? `url(${API_BASE}${show.banner})` : undefined,
              }}
            >
              {/* JioHotstar signature cinematic gradient masks */}
              <div className="hotstar-gradient-left" />
              <div className="hotstar-gradient-bottom" />
              <div className="hotstar-gradient-top" />
            </div>
          );
        })}
      </div>

      {/* Hero Foreground Content */}
      <div className="hotstar-hero-content-area">
        <div className="hotstar-info-block">
          {/* Stylized Title Logo / Header */}
          <div className="hotstar-title-wrap">
            <h1 className="hotstar-title-logo">{currentShow.title}</h1>
          </div>

          {/* Metadata Row: 2026 • U/A 7+ • 2 Seasons • 4 Languages */}
          <div className="hotstar-meta-row">
            <span className="meta-year">2026</span>
            <span className="meta-dot">•</span>
            <span className="meta-rating">U/A 7+</span>
            <span className="meta-dot">•</span>
            <span className="meta-duration">
              {regularSeasons.length > 0
                ? `${regularSeasons.length} ${regularSeasons.length === 1 ? 'Season' : 'Seasons'}`
                : `${totalEpisodes} Episodes`}
            </span>
            <span className="meta-dot">•</span>
            <span className="meta-languages">
              {availableLangs.length > 1
                ? `${availableLangs.length} Languages`
                : availableLangs.length === 1
                ? availableLangs[0].toUpperCase()
                : 'Multi Audio'}
            </span>
          </div>

          {/* Synopsis */}
          {currentShow.synopsis && (
            <p className="hotstar-synopsis">{currentShow.synopsis}</p>
          )}

          {/* Genre Line: Action | Comedy | Thriller */}
          <div className="hotstar-genres-row">
            {genres.map((g, i) => (
              <React.Fragment key={g}>
                <span className="genre-item">{g}</span>
                {i < genres.length - 1 && <span className="genre-pipe">|</span>}
              </React.Fragment>
            ))}
          </div>

          {/* Action Buttons: ▶ Watch Now (Signature Hotstar Gradient) + Plus Button */}
          <div className="hotstar-action-row">
            <button
              className="hotstar-watch-btn"
              onClick={() => onSelectShow(currentShow)}
            >
              <span className="watch-icon">▶</span>
              <span>Watch Now</span>
            </button>
            <button
              className="hotstar-add-btn"
              onClick={() => onSelectShow(currentShow)}
              title="More Info & Episodes"
              aria-label="More Info"
            >
              +
            </button>
          </div>
        </div>

        {/* Bottom-Right Horizontal Miniature Slider (Exact JioHotstar Layout) */}
        <div className="hotstar-thumb-slider-container">
          <div className="hotstar-thumb-track" ref={thumbListRef}>
            {carouselShows.map((show, idx) => {
              const isSelected = idx === currentIndex;
              return (
                <div
                  key={show.id || idx}
                  className={`hotstar-thumb-card ${isSelected ? 'active' : ''}`}
                  onClick={() => goToSlide(idx)}
                >
                  <div className="thumb-card-inner">
                    {show.thumbnail ? (
                      <img src={`${API_BASE}${show.thumbnail}`} alt={show.title} />
                    ) : show.poster ? (
                      <img src={`${API_BASE}${show.poster}`} alt={show.title} />
                    ) : (
                      <div className="thumb-card-placeholder">🎬</div>
                    )}
                    {isSelected && !isHovered && !isModalOpen && (
                      <div
                        className="hotstar-thumb-progress"
                        style={{ animationDuration: `${SLIDE_DURATION}ms` }}
                      />
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Navigation Next Arrow on the Thumb Strip */}
          <button
            className="hotstar-thumb-next-btn"
            onClick={nextSlide}
            aria-label="Next featured show"
          >
            ›
          </button>
        </div>
      </div>
    </div>
  );
}
