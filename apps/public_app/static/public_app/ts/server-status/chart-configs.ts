/**
 * Chart.js Configuration Templates
 */

export const MAX_DATA_POINTS = 1800;
export const UPDATE_INTERVAL = 2000;

// SCITEX-inspired chart styling
// Reference: scitex/plt/styles/SCITEX_STYLE.yaml
export const percentChartConfig: any = {
  type: 'line',
  options: {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 200 },
    interaction: { intersect: false, mode: 'index' },
    layout: {
      padding: { left: 4, right: 8, top: 4, bottom: 4 }
    },
    scales: {
      x: {
        type: 'time',
        time: { unit: 'minute', displayFormats: { minute: 'HH:mm' } },
        title: { display: false },
        grid: { display: false },
        border: { display: true, color: '#555', width: 1 },
        ticks: {
          maxTicksLimit: 4,
          color: '#888',
          font: { size: 10 }
        }
      },
      y: {
        min: 0,
        max: 100,
        title: { display: false },
        grid: { display: false },
        border: { display: true, color: '#555', width: 1 },
        ticks: {
          maxTicksLimit: 4,
          color: '#888',
          font: { size: 10 },
          callback: function(value: number) {
            return value + '%';
          }
        }
      }
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(0,0,0,0.8)',
        titleFont: { size: 10 },
        bodyFont: { size: 10 },
        padding: 6,
        callbacks: {
          label: function(context: any) {
            return context.parsed.y.toFixed(1) + '%';
          }
        }
      }
    }
  }
};

export const networkChartConfig: any = {
  type: 'line',
  options: {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 200 },
    interaction: { intersect: false, mode: 'index' },
    layout: {
      padding: { left: 4, right: 8, top: 4, bottom: 4 }
    },
    scales: {
      x: {
        type: 'time',
        time: { unit: 'minute', displayFormats: { minute: 'HH:mm' } },
        title: { display: false },
        grid: { display: false },
        border: { display: true, color: '#555', width: 1 },
        ticks: {
          maxTicksLimit: 4,
          color: '#888',
          font: { size: 10 }
        }
      },
      y: {
        min: 0,
        title: { display: false },
        grid: { display: false },
        border: { display: true, color: '#555', width: 1 },
        ticks: {
          maxTicksLimit: 4,
          color: '#888',
          font: { size: 10 }
        }
      }
    },
    plugins: {
      legend: {
        display: true,
        position: 'top',
        align: 'end',
        labels: {
          boxWidth: 12,
          boxHeight: 2,
          padding: 8,
          font: { size: 9 },
          color: '#888'
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0,0,0,0.8)',
        titleFont: { size: 10 },
        bodyFont: { size: 10 },
        padding: 6,
        callbacks: {
          label: function(context: any) {
            return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + ' MB/s';
          }
        }
      }
    }
  }
};
