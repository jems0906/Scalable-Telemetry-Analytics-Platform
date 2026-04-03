import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

export default function LiveChart({ title, labels, latencyData, cpuData }) {
  const data = {
    labels,
    datasets: [
      {
        label: 'Avg Latency (ms)',
        data: latencyData,
        borderColor: '#f25f4c',
        backgroundColor: 'rgba(242, 95, 76, 0.2)',
        tension: 0.35,
        yAxisID: 'yLatency'
      },
      {
        label: 'Avg CPU (%)',
        data: cpuData,
        borderColor: '#247ba0',
        backgroundColor: 'rgba(36, 123, 160, 0.2)',
        tension: 0.35,
        yAxisID: 'yCpu'
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 450
    },
    plugins: {
      legend: {
        position: 'bottom'
      },
      title: {
        display: true,
        text: title
      }
    },
    scales: {
      yLatency: {
        type: 'linear',
        position: 'left'
      },
      yCpu: {
        type: 'linear',
        position: 'right',
        min: 0,
        max: 100,
        grid: {
          drawOnChartArea: false
        }
      }
    }
  };

  return (
    <div className="chart-card">
      <Line data={data} options={options} />
    </div>
  );
}
