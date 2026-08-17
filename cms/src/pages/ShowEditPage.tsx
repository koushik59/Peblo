import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getShow, createShow, updateShow,
  createSeason, createEpisode, updateEpisode, deleteEpisode,
  uploadShowArtwork,
} from '../api';

const SECTIONS = ['featured', 'series', 'minisodes', 'songs'];
const CATEGORIES = ['adventure', 'folk', 'friendship', 'india', 'language', 'learning', 'maths', 'music', 'nature', 'reading', 'science', 'singalong', 'stories', 'travel', 'values'];
const LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'hi', name: 'Hindi' },
  { code: 'ta', name: 'Tamil' },
  { code: 'te', name: 'Telugu' },
  { code: 'kn', name: 'Kannada' },
];

const ARTWORK_SPECS: Record<string, { label: string; dims: string; ratio: string }> = {
  poster: { label: 'Poster', dims: '600×900', ratio: '2:3' },
  banner: { label: 'Banner', dims: '1280×720', ratio: '16:9' },
  thumbnail: { label: 'Thumbnail', dims: '640×360', ratio: '16:9' },
};

const API_BASE = '/api';

export default function ShowEditPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isNew = !id;

  const [form, setForm] = useState({
    title: '',
    synopsis: '',
    category: '',
    section: '',
    is_published: false,
  });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [artworkErrors, setArtworkErrors] = useState<Record<string, string>>({});
  const [uploadingArt, setUploadingArt] = useState<Record<string, boolean>>({});

  // Episode form state
  const [showEpForm, setShowEpForm] = useState<string | null>(null); // season ID
  const [epForm, setEpForm] = useState({ title: '', duration: '', content_group: '', language: 'en' });

  const { data: show, isLoading, error, refetch } = useQuery({
    queryKey: ['show', id],
    queryFn: async () => {
      if (!id) return null;
      const res = await getShow(id);
      return res.data;
    },
    enabled: !!id,
  });

  useEffect(() => {
    if (show) {
      setForm({
        title: show.title || '',
        synopsis: show.synopsis || '',
        category: show.category || '',
        section: show.section || '',
        is_published: show.is_published || false,
      });
    }
  }, [show]);

  const handleSave = async () => {
    setSaving(true);
    setSaveError('');
    try {
      if (isNew) {
        const res = await createShow(form);
        navigate(`/shows/${res.data.id}`);
      } else {
        await updateShow(id!, form);
        refetch();
      }
    } catch (err: any) {
      setSaveError(err.response?.data?.detail || 'Failed to save show');
    } finally {
      setSaving(false);
    }
  };

  const handleArtworkUpload = async (artworkType: string, file: File) => {
    if (!id) return;
    setUploadingArt((prev) => ({ ...prev, [artworkType]: true }));
    setArtworkErrors((prev) => ({ ...prev, [artworkType]: '' }));
    try {
      await uploadShowArtwork(id, artworkType, file);
      refetch();
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Upload failed';
      setArtworkErrors((prev) => ({ ...prev, [artworkType]: detail }));
    } finally {
      setUploadingArt((prev) => ({ ...prev, [artworkType]: false }));
    }
  };

  const handleAddSeason = async () => {
    if (!id) return;
    const num = prompt('Enter season number (0 for trailers):');
    if (num === null) return;
    try {
      await createSeason(id, { season_number: parseInt(num) });
      refetch();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create season');
    }
  };

  const handleAddEpisode = async (seasonId: string) => {
    try {
      await createEpisode(seasonId, {
        ...epForm,
        duration: epForm.duration ? parseInt(epForm.duration) : null,
      });
      setShowEpForm(null);
      setEpForm({ title: '', duration: '', content_group: '', language: 'en' });
      refetch();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create episode');
    }
  };

  const handleDeleteEp = async (epId: string, title: string) => {
    if (!confirm(`Delete episode "${title}"?`)) return;
    try {
      await deleteEpisode(epId);
      refetch();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete episode');
    }
  };

  const handleToggleEpPublish = async (epId: string, currentState: boolean) => {
    try {
      await updateEpisode(epId, { is_published: !currentState });
      refetch();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update episode');
    }
  };

  if (isLoading) return <div className="loading">Loading show...</div>;
  if (error) return <div className="error-state">Failed to load show.</div>;

  const getArtwork = (type: string) => {
    if (!show?.artworks) return null;
    return show.artworks.find((a: any) => a.artwork_type === type);
  };

  return (
    <div>
      <div className="page-header">
        <h1>{isNew ? 'Create Show' : `Edit: ${show?.title}`}</h1>
        <button className="btn-secondary" onClick={() => navigate('/shows')}>
          ← Back to Shows
        </button>
      </div>

      {saveError && <div className="login-error" style={{ marginBottom: 16 }}>{saveError}</div>}

      <div className="card">
        <h3 style={{ marginBottom: 16 }}>Show Details</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div className="form-group">
            <label htmlFor="show-title">Title *</label>
            <input
              id="show-title"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="Show title"
            />
          </div>
          <div className="form-group">
            <label htmlFor="show-category">Category</label>
            <select
              id="show-category"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
            >
              <option value="">Select category</option>
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="show-section">Section *</label>
            <select
              id="show-section"
              value={form.section}
              onChange={(e) => setForm({ ...form, section: e.target.value })}
            >
              <option value="">Select section</option>
              {SECTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="show-published">Status</label>
            <select
              id="show-published"
              value={form.is_published ? 'true' : 'false'}
              onChange={(e) => setForm({ ...form, is_published: e.target.value === 'true' })}
            >
              <option value="false">Draft</option>
              <option value="true">Published</option>
            </select>
          </div>
        </div>
        <div className="form-group">
          <label htmlFor="show-synopsis">Synopsis</label>
          <textarea
            id="show-synopsis"
            rows={3}
            value={form.synopsis}
            onChange={(e) => setForm({ ...form, synopsis: e.target.value })}
            placeholder="Show description..."
          />
        </div>
        <button className="btn-primary" onClick={handleSave} disabled={saving || !form.title}>
          {saving ? 'Saving...' : isNew ? 'Create Show' : 'Save Changes'}
        </button>
      </div>

      {/* Artwork - only shown after show is created */}
      {!isNew && (
        <div className="card">
          <h3 style={{ marginBottom: 8 }}>Artwork</h3>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
            Max 200 KB per image. Upload all three types for publishing.
          </p>
          <div className="artwork-slots">
            {Object.entries(ARTWORK_SPECS).map(([type, spec]) => {
              const existing = getArtwork(type);
              return (
                <div className="artwork-slot" key={type}>
                  <h4>{spec.label}</h4>
                  <div className="specs">{spec.dims} · {spec.ratio} · Max 200 KB</div>
                  {existing && (
                    <img
                      src={`${API_BASE}${existing.url}`}
                      alt={spec.label}
                      loading="lazy"
                    />
                  )}
                  {uploadingArt[type] && <div style={{ color: 'var(--primary)', fontSize: 12 }}>Uploading...</div>}
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    id={`artwork-${type}`}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleArtworkUpload(type, file);
                    }}
                    style={{ fontSize: 12 }}
                  />
                  {artworkErrors[type] && (
                    <div className="error">{artworkErrors[type]}</div>
                  )}
                  {existing && (
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                      {existing.width}×{existing.height} · {(existing.file_size / 1024).toFixed(1)} KB
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Seasons & Episodes */}
      {!isNew && show?.seasons && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3>Seasons & Episodes</h3>
            <button className="btn-secondary" onClick={handleAddSeason}>+ Add Season</button>
          </div>

          {show.seasons.length === 0 && (
            <div className="empty-state" style={{ padding: 20 }}>
              <p>No seasons yet. Add a season to start adding episodes.</p>
            </div>
          )}

          {show.seasons.map((season: any) => (
            <div key={season.id} style={{ marginBottom: 20 }}>
              <h4 style={{ marginBottom: 8, color: 'var(--primary)' }}>
                {season.season_number === 0 ? '🎬 Trailers (Season 0)' : `Season ${season.season_number}`}
              </h4>

              {season.episodes.length > 0 && (
                <table style={{ marginBottom: 12 }}>
                  <thead>
                    <tr>
                      <th>Title</th>
                      <th>Duration</th>
                      <th>Content Group</th>
                      <th>Language</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {season.episodes.map((ep: any) => (
                      <tr key={ep.id}>
                        <td>{ep.title}</td>
                        <td>{ep.duration ? `${Math.floor(ep.duration / 60)}m ${ep.duration % 60}s` : <span className="badge badge-danger">Missing</span>}</td>
                        <td style={{ fontSize: 12, fontFamily: 'monospace' }}>{ep.content_group}</td>
                        <td>{ep.language}</td>
                        <td>
                          <span className={`badge ${ep.is_published ? 'badge-success' : 'badge-warning'}`}>
                            {ep.is_published ? 'Published' : 'Draft'}
                          </span>
                        </td>
                        <td>
                          <button
                            className="btn-secondary"
                            style={{ padding: '4px 10px', fontSize: 11, marginRight: 4 }}
                            onClick={() => handleToggleEpPublish(ep.id, ep.is_published)}
                          >
                            {ep.is_published ? 'Unpublish' : 'Publish'}
                          </button>
                          <button
                            className="btn-danger"
                            style={{ padding: '4px 10px', fontSize: 11 }}
                            onClick={() => handleDeleteEp(ep.id, ep.title)}
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {showEpForm === season.id ? (
                <div style={{ background: 'var(--bg-input)', padding: 16, borderRadius: 'var(--radius)' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 12 }}>
                    <div className="form-group">
                      <label>Title</label>
                      <input
                        value={epForm.title}
                        onChange={(e) => setEpForm({ ...epForm, title: e.target.value })}
                        placeholder="Episode title"
                      />
                    </div>
                    <div className="form-group">
                      <label>Duration (seconds)</label>
                      <input
                        type="number"
                        value={epForm.duration}
                        onChange={(e) => setEpForm({ ...epForm, duration: e.target.value })}
                        placeholder="2700"
                      />
                    </div>
                    <div className="form-group">
                      <label>Content Group</label>
                      <input
                        value={epForm.content_group}
                        onChange={(e) => setEpForm({ ...epForm, content_group: e.target.value })}
                        placeholder="show-s1e1"
                      />
                    </div>
                    <div className="form-group">
                      <label>Language</label>
                      <select
                        value={epForm.language}
                        onChange={(e) => setEpForm({ ...epForm, language: e.target.value })}
                      >
                        {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.name} ({l.code})</option>)}
                      </select>
                    </div>
                  </div>
                  <button className="btn-primary" style={{ marginRight: 8 }} onClick={() => handleAddEpisode(season.id)}>
                    Add Episode
                  </button>
                  <button className="btn-secondary" onClick={() => setShowEpForm(null)}>Cancel</button>
                </div>
              ) : (
                <button className="btn-secondary" style={{ fontSize: 12 }} onClick={() => setShowEpForm(season.id)}>
                  + Add Episode
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
