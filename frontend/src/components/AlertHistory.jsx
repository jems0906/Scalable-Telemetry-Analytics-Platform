import { useMemo, useState } from 'react';

function severityClass(severity) {
  switch ((severity || '').toLowerCase()) {
    case 'critical':
      return 'sev-critical';
    case 'major':
      return 'sev-major';
    default:
      return 'sev-warning';
  }
}

function eventLabel(type) {
  if (type === 'SLO_RECOVERY') {
    return 'Recovered';
  }
  return 'Breached';
}

export default function AlertHistory({ alerts, paused, onTogglePaused }) {
  const [serviceFilter, setServiceFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');

  const serviceOptions = useMemo(() => {
    const values = new Set(alerts.map((alert) => alert.service_name).filter(Boolean));
    return ['all', ...Array.from(values).sort()];
  }, [alerts]);

  const filteredAlerts = useMemo(() => {
    return alerts.filter((alert) => {
      const matchesService = serviceFilter === 'all' || alert.service_name === serviceFilter;
      const matchesSeverity = severityFilter === 'all' || (alert.severity || 'warning') === severityFilter;
      const eventType = alert.type === 'SLO_RECOVERY' ? 'recovery' : 'breach';
      const matchesType = typeFilter === 'all' || eventType === typeFilter;
      return matchesService && matchesSeverity && matchesType;
    });
  }, [alerts, serviceFilter, severityFilter, typeFilter]);

  return (
    <section className="alert-card">
      <div className="alert-header">
        <h3>Alert History</h3>
        <div className="alert-header-actions">
          <span>{filteredAlerts.length} shown</span>
          <button className="alert-toggle" onClick={onTogglePaused}>
            {paused ? 'Resume Feed' : 'Pause Feed'}
          </button>
        </div>
      </div>

      <div className="alert-controls">
        <select value={serviceFilter} onChange={(event) => setServiceFilter(event.target.value)}>
          {serviceOptions.map((serviceName) => (
            <option key={serviceName} value={serviceName}>
              {serviceName}
            </option>
          ))}
        </select>
        <select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}>
          <option value="all">All severities</option>
          <option value="warning">Warning</option>
          <option value="major">Major</option>
          <option value="critical">Critical</option>
        </select>
        <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
          <option value="all">All events</option>
          <option value="breach">Breaches</option>
          <option value="recovery">Recoveries</option>
        </select>
      </div>

      {filteredAlerts.length === 0 ? (
        <p className="alert-empty">No recent emitted alerts.</p>
      ) : (
        <ul className="alert-list">
          {filteredAlerts.map((alert, index) => (
            <li key={`${alert.timestamp}-${alert.service_name}-${index}`} className="alert-item">
              <div className="alert-row">
                <span className={`badge ${severityClass(alert.severity)}`}>
                  {(alert.severity || 'warning').toUpperCase()}
                </span>
                <strong>{eventLabel(alert.type)}</strong>
                <span>{alert.service_name}</span>
                <time>{new Date(alert.timestamp).toLocaleTimeString()}</time>
              </div>
              <p>
                {alert.type === 'SLO_RECOVERY'
                  ? 'Service returned to healthy SLO state.'
                  : `P99 ${Number(alert.payload?.p99_latency_ms || 0).toFixed(1)} ms, Error ${(Number(alert.payload?.error_rate || 0) * 100).toFixed(2)}%`}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
