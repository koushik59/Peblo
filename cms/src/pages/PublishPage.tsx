import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getValidationReport, publishCatalogue, getPublishRuns } from '../api';

interface Props {
  user: { role: string; name: string; email: string };
}

export default function PublishPage({ user }: Props) {
  const queryClient = useQueryClient();
  const isAdmin = user.role === 'admin';

  const { data: report, isLoading: reportLoading, error: reportError } = useQuery({
    queryKey: ['validation-report'],
    queryFn: async () => {
      const res = await getValidationReport();
      return res.data;
    },
  });

  const { data: runs, isLoading: runsLoading } = useQuery({
    queryKey: ['publish-runs'],
    queryFn: async () => {
      const res = await getPublishRuns();
      return res.data;
    },
  });

  const publishMutation = useMutation({
    mutationFn: publishCatalogue,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['publish-runs'] });
      queryClient.invalidateQueries({ queryKey: ['validation-report'] });
    },
  });

  const canPublish = isAdmin && report && !report.has_blockers && !publishMutation.isPending;

  return (
    <div>
      <div className="page-header">
        <h1>🚀 Publish Catalogue</h1>
      </div>

      {/* Permission check */}
      {!isAdmin && (
        <div className="card" style={{ borderColor: 'var(--warning)' }}>
          <p style={{ color: 'var(--warning)' }}>
            ⚠️ You are logged in as an <strong>editor</strong>. Only admins can publish the catalogue.
            Please contact an admin to publish.
          </p>
        </div>
      )}

      {/* Validation Report */}
      <div className="card">
        <h3 style={{ marginBottom: 16 }}>Validation Report</h3>

        {reportLoading && <div className="loading">Loading validation report...</div>}
        {reportError && <div className="error-state">Failed to load validation report.</div>}

        {report && (
          <>
            <div className="publish-summary">
              <div className="summary-card">
                <div className="number">{report.summary.total_shows}</div>
                <div className="label">Total Shows</div>
              </div>
              <div className="summary-card">
                <div className="number" style={{ color: report.summary.blocking_issues ? 'var(--danger)' : 'var(--success)' }}>
                  {report.summary.blocking_issues}
                </div>
                <div className="label">Blocking Issues</div>
              </div>
              <div className="summary-card">
                <div className="number" style={{ color: 'var(--warning)' }}>
                  {report.summary.warning_issues}
                </div>
                <div className="label">Warnings</div>
              </div>
              <div className="summary-card">
                <div className="number">{report.summary.total_issues}</div>
                <div className="label">Total Issues</div>
              </div>
            </div>

            {report.issues.length === 0 && (
              <div style={{ color: 'var(--success)', textAlign: 'center', padding: 20 }}>
                ✅ No issues found. Ready to publish!
              </div>
            )}

            {report.issues.map((issue: any, i: number) => (
              <div key={i} className={`validation-issue ${issue.severity}`}>
                <div className="issue-header">
                  <span className={`badge ${issue.severity === 'error' ? 'badge-danger' : 'badge-warning'}`}>
                    {issue.severity === 'error' ? '🚫 Blocker' : '⚠️ Warning'}
                  </span>
                  {' '}
                  <strong>{issue.entity_type}</strong>
                  {issue.entity_name && ` — ${issue.entity_name}`}
                </div>
                <div style={{ margin: '6px 0', fontSize: 14 }}>{issue.message}</div>
                <div className="issue-fix">💡 Fix: {issue.how_to_fix}</div>
              </div>
            ))}
          </>
        )}
      </div>

      {/* Publish Button */}
      {isAdmin && (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <button
              className="btn-primary"
              disabled={!canPublish}
              onClick={() => publishMutation.mutate()}
              style={{ padding: '14px 32px', fontSize: 16 }}
            >
              {publishMutation.isPending ? '⏳ Publishing...' : '🚀 Publish Catalogue'}
            </button>
            {report?.has_blockers && (
              <span style={{ color: 'var(--danger)', fontSize: 14 }}>
                Cannot publish — {report.summary.blocking_issues} blocking issue(s) must be resolved first.
              </span>
            )}
          </div>

          {publishMutation.isError && (
            <div style={{ color: 'var(--danger)', marginTop: 12 }}>
              ❌ Publish failed: {(publishMutation.error as any)?.response?.data?.detail || 'Unknown error'}
            </div>
          )}

          {publishMutation.isSuccess && (
            <div style={{ color: 'var(--success)', marginTop: 12 }}>
              ✅ Catalogue published successfully!
            </div>
          )}
        </div>
      )}

      {/* Publish History */}
      <div className="card">
        <h3 style={{ marginBottom: 16 }}>Publish History</h3>

        {runsLoading && <div className="loading">Loading publish history...</div>}

        {runs && runs.length === 0 && (
          <div className="empty-state" style={{ padding: 20 }}>
            <p>No publish runs yet.</p>
          </div>
        )}

        {runs && runs.length > 0 && (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Publisher</th>
                  <th>Status</th>
                  <th>Shows</th>
                  <th>Episodes</th>
                  <th>Content Hash</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run: any) => (
                  <tr key={run.id}>
                    <td>{new Date(run.published_at).toLocaleString()}</td>
                    <td>{run.published_by}</td>
                    <td>
                      <span className={`badge ${run.status === 'success' ? 'badge-success' : 'badge-danger'}`}>
                        {run.status}
                      </span>
                    </td>
                    <td>{run.show_count}</td>
                    <td>{run.episode_count}</td>
                    <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{run.content_hash || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
