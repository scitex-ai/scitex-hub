/**
 * Chart Initialization Module
 * Creates and configures all Chart.js instances for server metrics
 */

import { getChart } from './types.js';
import { percentChartConfig, networkChartConfig } from './chart-configs.js';

export interface ChartInstances {
  cpuChart: any;
  memoryChart: any;
  diskChart: any;
  gpuChart: any;
  diskIoChart: any;
  netIoChart: any;
  visitorPoolChart: any;
  activeUsersChart: any;
}

export function initializeCharts(): ChartInstances | null {
  // Get Chart.js from window (loaded via CDN) - must be inside function, not at module level
  const Chart = getChart();
  if (!Chart) {
    console.error('[chart-init] Chart.js not loaded');
    return null;
  }

  // Initialize CPU chart
  const cpuCtx = (document.getElementById('cpuChart') as HTMLCanvasElement)?.getContext('2d');
  if (!cpuCtx) return null;

  const cpuChart = new Chart(cpuCtx, {
    ...percentChartConfig,
    data: {
      datasets: [{
        label: 'CPU Usage',
        data: [],
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.15)',
        borderWidth: 1.5,
        tension: 0.3,
        fill: true,
        spanGaps: false,
        pointRadius: 0,
        pointHitRadius: 10,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: 'rgb(54, 162, 235)',
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2
      }]
    }
  });

  // Initialize Memory chart
  const memoryCtx = (document.getElementById('memoryChart') as HTMLCanvasElement)?.getContext('2d');
  if (!memoryCtx) return null;

  const memoryChart = new Chart(memoryCtx, {
    ...percentChartConfig,
    data: {
      datasets: [{
        label: 'Memory Usage',
        data: [],
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.15)',
        borderWidth: 1.5,
        tension: 0.3,
        fill: true,
        spanGaps: false,
        pointRadius: 0,
        pointHitRadius: 10,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: 'rgb(255, 99, 132)',
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2
      }]
    }
  });

  // Initialize Disk chart
  const diskCtx = (document.getElementById('diskChart') as HTMLCanvasElement)?.getContext('2d');
  if (!diskCtx) return null;

  const diskChart = new Chart(diskCtx, {
    ...percentChartConfig,
    data: {
      datasets: [{
        label: 'Disk Usage',
        data: [],
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.15)',
        borderWidth: 1.5,
        tension: 0.3,
        fill: true,
        spanGaps: false,
        pointRadius: 0,
        pointHitRadius: 10,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: 'rgb(75, 192, 192)',
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2
      }]
    }
  });

  // Initialize GPU chart
  const gpuCtx = (document.getElementById('gpuChart') as HTMLCanvasElement)?.getContext('2d');
  if (!gpuCtx) return null;

  const gpuChart = new Chart(gpuCtx, {
    ...percentChartConfig,
    data: {
      datasets: [{
        label: 'GPU Usage',
        data: [],
        borderColor: 'rgb(153, 102, 255)',
        backgroundColor: 'rgba(153, 102, 255, 0.15)',
        borderWidth: 1.5,
        tension: 0.3,
        fill: true,
        spanGaps: false,
        pointRadius: 0,
        pointHitRadius: 10,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: 'rgb(153, 102, 255)',
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2
      }]
    }
  });

  // Initialize Disk I/O chart
  const diskIoCtx = (document.getElementById('diskIoChart') as HTMLCanvasElement)?.getContext('2d');
  if (!diskIoCtx) return null;

  const diskIoChart = new Chart(diskIoCtx, {
    ...networkChartConfig,
    data: {
      datasets: [
        {
          label: 'Read',
          data: [],
          borderColor: 'rgb(75, 192, 192)',
          backgroundColor: 'rgba(75, 192, 192, 0.15)',
          borderWidth: 1.5,
          tension: 0.3,
          fill: false,
          pointRadius: 0,
          pointHitRadius: 10,
          pointHoverRadius: 4
        },
        {
          label: 'Write',
          data: [],
          borderColor: 'rgb(255, 159, 64)',
          backgroundColor: 'rgba(255, 159, 64, 0.15)',
          borderWidth: 1.5,
          tension: 0.3,
          fill: false,
          pointRadius: 0,
          pointHitRadius: 10,
          pointHoverRadius: 4
        }
      ]
    }
  });

  // Initialize Network I/O chart
  const netIoCtx = (document.getElementById('netIoChart') as HTMLCanvasElement)?.getContext('2d');
  if (!netIoCtx) return null;

  const netIoChart = new Chart(netIoCtx, {
    ...networkChartConfig,
    data: {
      datasets: [
        {
          label: 'Sent',
          data: [],
          borderColor: 'rgb(255, 99, 132)',
          backgroundColor: 'rgba(255, 99, 132, 0.15)',
          borderWidth: 1.5,
          tension: 0.3,
          fill: false,
          pointRadius: 0,
          pointHitRadius: 10,
          pointHoverRadius: 4
        },
        {
          label: 'Received',
          data: [],
          borderColor: 'rgb(54, 162, 235)',
          backgroundColor: 'rgba(54, 162, 235, 0.15)',
          borderWidth: 1.5,
          tension: 0.3,
          fill: false,
          pointRadius: 0,
          pointHitRadius: 10,
          pointHoverRadius: 4
        }
      ]
    }
  });

  // Initialize Visitor Pool chart
  const visitorPoolCtx = (document.getElementById('visitorPoolChart') as HTMLCanvasElement)?.getContext('2d');
  if (!visitorPoolCtx) return null;

  const visitorPoolChart = new Chart(visitorPoolCtx, {
    ...percentChartConfig,
    data: {
      datasets: [{
        label: 'Allocated Slots',
        data: [],
        borderColor: 'rgb(201, 203, 207)',
        backgroundColor: 'rgba(201, 203, 207, 0.15)',
        borderWidth: 1.5,
        tension: 0.3,
        fill: true,
        spanGaps: false,
        pointRadius: 0,
        pointHitRadius: 10,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: 'rgb(201, 203, 207)',
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2
      }]
    },
    options: {
      ...percentChartConfig.options,
      scales: {
        ...percentChartConfig.options.scales,
        y: {
          ...percentChartConfig.options.scales.y,
          max: 4,
          title: {
            display: true,
            text: 'Allocated Slots'
          },
          ticks: {
            stepSize: 1,
            callback: function(value: number) {
              return value;
            }
          }
        }
      }
    }
  });

  // Initialize Active Users chart
  const activeUsersCtx = (document.getElementById('activeUsersChart') as HTMLCanvasElement)?.getContext('2d');
  if (!activeUsersCtx) return null;

  const activeUsersChart = new Chart(activeUsersCtx, {
    ...percentChartConfig,
    data: {
      datasets: [{
        label: 'Active Users',
        data: [],
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.15)',
        borderWidth: 1.5,
        tension: 0.3,
        fill: true,
        spanGaps: false,
        pointRadius: 0,
        pointHitRadius: 10,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: 'rgb(75, 192, 192)',
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2
      }]
    },
    options: {
      ...percentChartConfig.options,
      scales: {
        ...percentChartConfig.options.scales,
        y: {
          ...percentChartConfig.options.scales.y,
          title: {
            display: true,
            text: 'Number of Users'
          },
          ticks: {
            stepSize: 1,
            callback: function(value: number) {
              return Math.floor(value);
            }
          }
        }
      }
    }
  });

  return {
    cpuChart,
    memoryChart,
    diskChart,
    gpuChart,
    diskIoChart,
    netIoChart,
    visitorPoolChart,
    activeUsersChart
  };
}
