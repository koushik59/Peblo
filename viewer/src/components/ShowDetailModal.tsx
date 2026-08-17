import { useState } from 'react';
import { Show, Season, Episode, Trailer } from '../api';

const API_BASE = '/api';

interface Props {
  show: Show;
  onClose: () => void;
}

function formatDuration(seconds: number | null): string {
  if (!seconds || seconds <= 0) return '—';
  const mins = Math.floor(seconds / 60);
  const hrs = Math.floor(mins / 60);
  const remainingMins = mins % 60;
  if (hrs > 0) {
    return `${hrs}h ${remainingMins > 0 ? `${remainingMins}m` : ''}`;
  }
  return `${mins}m`;
}

export default function ShowDetailModal({ show, onClose }: Props) {
  // Numbered seasons (excluding season 0)
  const regularSeasons = (show.seasons || []).filter((s) => s.number !== 0);
  const trailers: Trailer[] = show.trailers || [];

  // Tab options: Regular seasons + Trailers tab if trailers exist
  const hasTrailers = trailers.length > 0;
  const defaultTab = regularSeasons.length > 0 ? `season-${regularSeasons[0].number}` : 'trailers';
  const [activeTab, setActiveTab] = useState<string>(defaultTab);

  const activeSeason = regularSeasons.find((s) => `season-${s.number}` === activeTab);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close-btn" onClick={onClose} aria-label="Close">
          ✕
        </button>

        {/* Modal Banner Hero */}
        <div
          className="modal-banner"
          style={{
            backgroundImage: show.banner ? `url(${API_BASE}${show.banner})` : undefined,
            backgroundColor: '#151824',
          }}
        >
          <div className="modal-banner-overlay" />
        </div>

        {/* Modal Content */}
        <div className="modal-body">
          <h2 className="modal-title">{show.title}</h2>
          <div className="modal-meta">
            {show.category && <span className="badge badge-category">{show.category}</span>}
            {regularSeasons.length > 0 && (
              <span className="badge">
                {regularSeasons.length} {regularSeasons.length === 1 ? 'Season' : 'Seasons'}
              </span>
            )}
            {hasTrailers && <span className="badge badge-lang">Trailers Available</span>}
          </div>

          <p className="modal-synopsis">
            {show.synopsis || 'No synopsis provided for this title.'}
          </p>

          {/* Season & Trailer Tabs */}
          {(regularSeasons.length > 0 || hasTrailers) && (
            <div className="season-tabs">
              {regularSeasons.map((season) => (
                <button
                  key={season.number}
                  className={`season-tab ${activeTab === `season-${season.number}` ? 'active' : ''}`}
                  onClick={() => setActiveTab(`season-${season.number}`)}
                >
                  Season {season.number}
                </button>
              ))}
              {hasTrailers && (
                <button
                  className={`season-tab ${activeTab === 'trailers' ? 'active' : ''}`}
                  onClick={() => setActiveTab('trailers')}
                >
                  🎬 Trailers & Extras
                </button>
              )}
            </div>
          )}

          {/* Episode List for Active Regular Season */}
          {activeSeason && (
            <div className="episodes-list">
              {activeSeason.episodes.map((ep, idx) => (
                <div key={ep.id || idx} className="episode-item">
                  <div className="episode-thumb">
                    {ep.thumbnail ? (
                      <img src={`${API_BASE}${ep.thumbnail}`} alt={ep.title} loading="lazy" />
                    ) : (
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>EP {idx + 1}</span>
                    )}
                  </div>
                  <div className="episode-info">
                    <div className="episode-title">
                      {idx + 1}. {ep.title}
                    </div>
                    <div className="episode-meta">
                      <span>⏱ {formatDuration(ep.duration)}</span>
                      <div className="lang-tags">
                        <span>Audio:</span>
                        {ep.languages && ep.languages.length > 0 ? (
                          ep.languages.map((lang) => (
                            <span key={lang} className="badge badge-lang">
                              {lang.toUpperCase()}
                            </span>
                          ))
                        ) : (
                          <span className="badge">EN</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Trailer List */}
          {activeTab === 'trailers' && hasTrailers && (
            <div className="episodes-list">
              {trailers.map((trailer, idx) => (
                <div key={trailer.id || idx} className="episode-item">
                  <div className="episode-thumb">
                    {trailer.thumbnail ? (
                      <img src={`${API_BASE}${trailer.thumbnail}`} alt={trailer.title} loading="lazy" />
                    ) : (
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>🎬</span>
                    )}
                  </div>
                  <div className="episode-info">
                    <div className="episode-title">{trailer.title}</div>
                    <div className="episode-meta">
                      <span>⏱ {formatDuration(trailer.duration)}</span>
                      <div className="lang-tags">
                        <span>Language:</span>
                        <span className="badge badge-lang">{trailer.language?.toUpperCase() || 'EN'}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
