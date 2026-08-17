import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getShows, deleteShow } from '../api';

const SECTIONS = ['', 'featured', 'series', 'minisodes', 'songs'];
const CATEGORIES = ['', 'adventure', 'folk', 'friendship', 'india', 'language', 'learning', 'maths', 'music', 'nature', 'reading', 'science', 'singalong', 'stories', 'travel', 'values'];

export default function ShowsPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [section, setSection] = useState('');
  const [category, setCategory] = useState('');
  const [publishedFilter, setPublishedFilter] = useState<string>('');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['shows', page, search, section, category, publishedFilter],
    queryFn: async () => {
      const params: Record<string, any> = { page, page_size: 20 };
      if (search) params.q = search;
      if (section) params.section = section;
      if (category) params.category = category;
      if (publishedFilter !== '') params.is_published = publishedFilter === 'true';
      const res = await getShows(params);
      return res.data;
    },
  });

  const handleDelete = async (id: string, title: string) => {
    if (!confirm(`Delete "${title}"? This cannot be undone.`)) return;
    try {
      await deleteShow(id);
      refetch();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete show');
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Shows</h1>
        <button className="btn-primary" onClick={() => navigate('/shows/new')}>
          + New Show
        </button>
      </div>

      <div className="filters-bar">
        <input
          id="search-shows"
          type="text"
          placeholder="Search shows..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        />
        <select
          id="filter-section"
          value={section}
          onChange={(e) => { setSection(e.target.value); setPage(1); }}
        >
          <option value="">All Sections</option>
          {SECTIONS.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          id="filter-category"
          value={category}
          onChange={(e) => { setCategory(e.target.value); setPage(1); }}
        >
          <option value="">All Categories</option>
          {CATEGORIES.filter(Boolean).map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <select
          id="filter-status"
          value={publishedFilter}
          onChange={(e) => { setPublishedFilter(e.target.value); setPage(1); }}
        >
          <option value="">All Status</option>
          <option value="true">Published</option>
          <option value="false">Draft</option>
        </select>
      </div>

      {isLoading && <div className="loading">Loading shows...</div>}
      {error && <div className="error-state">Failed to load shows. Please try again.</div>}

      {data && data.items.length === 0 && (
        <div className="empty-state">
          <h3>No shows found</h3>
          <p>Try changing your search or filters, or create a new show.</p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Category</th>
                  <th>Section</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((show: any) => (
                  <tr key={show.id}>
                    <td>
                      <a href="#" onClick={(e) => { e.preventDefault(); navigate(`/shows/${show.id}`); }}>
                        {show.title}
                      </a>
                    </td>
                    <td>{show.category || '—'}</td>
                    <td>{show.section || <span className="badge badge-danger">Missing</span>}</td>
                    <td>
                      <span className={`badge ${show.is_published ? 'badge-success' : 'badge-warning'}`}>
                        {show.is_published ? 'Published' : 'Draft'}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn-secondary"
                        style={{ padding: '6px 12px', fontSize: 12, marginRight: 8 }}
                        onClick={() => navigate(`/shows/${show.id}`)}
                      >
                        Edit
                      </button>
                      <button
                        className="btn-danger"
                        style={{ padding: '6px 12px', fontSize: 12 }}
                        onClick={() => handleDelete(show.id, show.title)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="pagination">
            <button
              className="btn-secondary"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              ← Previous
            </button>
            <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              Page {data.page} of {data.total_pages} ({data.total} shows)
            </span>
            <button
              className="btn-secondary"
              disabled={page >= data.total_pages}
              onClick={() => setPage(page + 1)}
            >
              Next →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
