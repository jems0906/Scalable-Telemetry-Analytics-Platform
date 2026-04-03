import { useEffect, useMemo, useState } from 'react';
import AlertHistory from './components/AlertHistory';
import LiveChart from './components/LiveChart';
import SLOTable from './components/SLOTable';
import {
  evaluateSlosNow,
  fetchAlerts,
  fetchRollups,
  fetchServices,
  fetchSlos,
  getAuthRole,
  getAuthToken,
  login,
  metricsSocketUrl,
  recomputeRollups,
  setAuthToken
} from './api';

const MAX_POINTS = 20;

function formatTime(date = new Date()) {
  return date.toLocaleTimeString();
}

export default function App() {
  const [token, setToken] = useState(getAuthToken());
  const [role, setRole] = useState(getAuthRole());
  const [loginForm, setLoginForm] = useState({ username: 'admin', password: 'admin123' });
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [actionStatus, setActionStatus] = useState('');

  const [services, setServices] = useState(['all']);
  const [selectedService, setSelectedService] = useState('all');
  const [selectedWindow, setSelectedWindow] = useState('1m');
  const [slos, setSlos] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [alertsPaused, setAlertsPaused] = useState(false);
  const [liveRollups, setLiveRollups] = useState([]);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (!token) {
      return;
    }

    async function bootstrap() {
      try {
        const serviceData = await fetchServices();
        setServices(['all', ...(serviceData.services || [])]);
      } catch {
        setAuthToken('');
        setToken('');
      }
    }

    bootstrap();
  }, [token]);

  useEffect(() => {
    if (!token) {
      return () => {};
    }

    const intervalId = setInterval(async () => {
      let rollupResponse;
      let sloResponse;
      try {
        [rollupResponse, sloResponse] = await Promise.all([
          fetchRollups(selectedWindow, selectedService === 'all' ? '' : selectedService),
          fetchSlos(selectedService === 'all' ? '' : selectedService)
        ]);
      } catch {
        return;
      }

      const rollups = rollupResponse.rollups || [];
      const serviceRollup =
        rollups.find((item) => item.service_name === selectedService) || rollups[0];

      if (serviceRollup) {
        setHistory((prev) => {
          const next = [...prev, { at: formatTime(), data: serviceRollup }];
          return next.slice(-MAX_POINTS);
        });
      }

      setLiveRollups(rollups);
      setSlos(sloResponse.slos || []);
    }, 4000);

    return () => clearInterval(intervalId);
  }, [selectedService, selectedWindow, token]);

  useEffect(() => {
    if (!token) {
      return () => {};
    }

    const loadAlerts = async () => {
      try {
        const alertResponse = await fetchAlerts(20);
        setAlerts(alertResponse.alerts || []);
      } catch {
        return;
      }
    };

    loadAlerts();
    if (alertsPaused) {
      return () => {};
    }

    const intervalId = setInterval(loadAlerts, 6000);
    return () => clearInterval(intervalId);
  }, [alertsPaused, token]);

  useEffect(() => {
    if (!token) {
      return () => {};
    }

    const ws = new WebSocket(metricsSocketUrl());
    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      const rollups = payload.rollups || [];
      setLiveRollups(rollups);
    };

    return () => ws.close();
  }, [token]);

  const chartLabels = useMemo(() => history.map((entry) => entry.at), [history]);
  const latencyData = useMemo(() => history.map((entry) => entry.data.avg_latency_ms), [history]);
  const cpuData = useMemo(() => history.map((entry) => entry.data.avg_cpu), [history]);

  const activeSlo = slos.find((item) => item.service_name === selectedService);
  const errorBudget = activeSlo ? Math.max(0, (activeSlo.error_rate_slo_target - activeSlo.error_rate) * 100) : 0;

  const handleLogin = async (event) => {
    event.preventDefault();
    setLoginLoading(true);
    setLoginError('');
    try {
      const response = await login(loginForm.username, loginForm.password);
      setAuthToken(response.access_token, response.role);
      setToken(response.access_token);
      setRole(response.role || 'viewer');
    } catch {
      setLoginError('Login failed. Check username and password.');
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    setAuthToken('');
    setToken('');
    setRole('');
    setHistory([]);
    setAlerts([]);
  };

  const runRecompute = async () => {
    setActionStatus('Running rollup recompute...');
    try {
      const response = await recomputeRollups();
      setActionStatus(`Rollup recompute complete: ${response.computed} records.`);
    } catch {
      setActionStatus('Rollup recompute failed. Check permissions or backend status.');
    }
  };

  const runSloEvaluation = async () => {
    setActionStatus('Running SLO evaluation...');
    try {
      const response = await evaluateSlosNow();
      setActionStatus(`SLO evaluation complete: ${response.evaluated} services.`);
    } catch {
      setActionStatus('SLO evaluation failed. Check permissions or backend status.');
    }
  };

  if (!token) {
    return (
      <div className="app-shell">
        <header>
          <h1>TrailMetrics</h1>
          <p>Sign in to access telemetry operations dashboard</p>
        </header>

        <section className="login-card">
          <h2>Operator Login</h2>
          <form onSubmit={handleLogin} className="login-form">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              value={loginForm.username}
              onChange={(event) => setLoginForm((prev) => ({ ...prev, username: event.target.value }))}
              required
            />

            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={loginForm.password}
              onChange={(event) => setLoginForm((prev) => ({ ...prev, password: event.target.value }))}
              required
            />

            <button type="submit" disabled={loginLoading}>
              {loginLoading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
          {loginError && <p className="login-error">{loginError}</p>}
        </section>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header>
        <h1>TrailMetrics</h1>
        <p>Scalable analytics and telemetry command center</p>
        <button className="logout-btn" onClick={handleLogout}>Log out</button>
      </header>

      <section className="ops-controls">
        <div>
          <h3>Operator Controls</h3>
          <p>Signed in role: <strong>{role || 'viewer'}</strong></p>
        </div>
        <div className="ops-buttons">
          <button onClick={runRecompute} disabled={role !== 'operator'}>Recompute Rollups</button>
          <button onClick={runSloEvaluation} disabled={role !== 'operator'}>Evaluate SLO Now</button>
        </div>
        {actionStatus && <p className="ops-status">{actionStatus}</p>}
      </section>

      <section className="toolbar">
        <label htmlFor="service">Service Drill-Down</label>
        <select id="service" value={selectedService} onChange={(event) => setSelectedService(event.target.value)}>
          {services.map((service) => (
            <option key={service} value={service}>
              {service}
            </option>
          ))}
        </select>

        <label htmlFor="window">Trend Window</label>
        <select id="window" value={selectedWindow} onChange={(event) => setSelectedWindow(event.target.value)}>
          <option value="1m">1 minute</option>
          <option value="5m">5 minutes</option>
          <option value="1h">1 hour</option>
        </select>

        <div className="budget-box">
          <span>Error Budget Remaining</span>
          <strong>{errorBudget.toFixed(2)}%</strong>
        </div>
      </section>

      <LiveChart
        title={`Live ${selectedWindow} Rollup: ${selectedService}`}
        labels={chartLabels}
        latencyData={latencyData}
        cpuData={cpuData}
      />

      <section className="cards">
        {liveRollups
          .filter((item) => selectedService === 'all' || item.service_name === selectedService)
          .map((rollup) => (
            <article key={`${rollup.window}-${rollup.service_name}`} className="metric-card">
              <h3>{rollup.service_name}</h3>
              <p>Samples: {rollup.samples}</p>
              <p>P99 Latency: {rollup.p99_latency_ms.toFixed(1)} ms</p>
              <p>Error Rate: {(rollup.error_rate * 100).toFixed(2)}%</p>
            </article>
          ))}
      </section>

      <SLOTable slos={slos} />
      <AlertHistory
        alerts={alerts}
        paused={alertsPaused}
        onTogglePaused={() => setAlertsPaused((prev) => !prev)}
      />
    </div>
  );
}
