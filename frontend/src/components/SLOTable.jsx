export default function SLOTable({ slos }) {
  return (
    <div className="slo-card">
      <h3>SLO Monitoring</h3>
      <table>
        <thead>
          <tr>
            <th>Service</th>
            <th>P99 Latency</th>
            <th>Error Rate</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {slos.map((slo) => {
            const status = slo.healthy ? 'Healthy' : 'Breached';
            return (
              <tr key={slo.service_name} className={slo.healthy ? 'ok' : 'breach'}>
                <td>{slo.service_name}</td>
                <td>{slo.p99_latency_ms.toFixed(1)} ms / target {slo.latency_slo_target_ms} ms</td>
                <td>{(slo.error_rate * 100).toFixed(2)}% / target {(slo.error_rate_slo_target * 100).toFixed(2)}%</td>
                <td>{status}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
