// Sample dashboard data used in demo mode when the orchestrator is unreachable,
// so Portfolio and Sites views stay presentable in a laptop-only demo.

export const DEMO_PERFORMANCE_DATA = {
  generated_at: '2026-07-01T09:00:00Z',
  overview: {
    portfolio_value: 148_500_000,
    total_units: 1462,
    occupied_units: 1381,
    occupancy: 94.5,
    total_noi: 9_240_000,
    pipeline_value: 36_750_000,
    pipeline_commission: 918_750,
    active_deals: 7,
    closed_ytd: 4,
    properties_count: 12,
  },
  pipeline: {
    pipeline_total: 36_750_000,
    commission_pipeline: 918_750,
    by_stage: {
      Prospecting: { count: 2, value: 8_400_000, commission: 210_000 },
      'Under LOI': { count: 2, value: 11_150_000, commission: 278_750 },
      'Due diligence': { count: 2, value: 10_700_000, commission: 267_500 },
      'Under contract': { count: 1, value: 6_500_000, commission: 162_500 },
    },
  },
  activities: {
    upcoming_count: 9,
    completed_count: 34,
    by_type: {
      'Property tour': 4,
      Inspection: 2,
      'Investor call': 3,
    },
  },
  top_properties_by_noi: [
    { name: 'Poplar Ridge Apartments', city: 'Memphis', noi: 1_680_000, value: 24_000_000, cap: 7.0 },
    { name: 'Cooper-Young Flats', city: 'Memphis', noi: 1_365_000, value: 19_500_000, cap: 7.0 },
    { name: 'Germantown Commons', city: 'Germantown', noi: 1_183_000, value: 18_200_000, cap: 6.5 },
    { name: 'Bartlett Station Lofts', city: 'Bartlett', noi: 942_000, value: 14_500_000, cap: 6.5 },
    { name: 'Midtown Crossing', city: 'Memphis', noi: 858_000, value: 13_200_000, cap: 6.5 },
  ],
}

export const DEMO_NETWORK_DATA = {
  generated_at: '2026-07-01T09:00:00Z',
  summary: {
    sites: 12,
    devices: 148,
    events: 412,
    daily_metrics: 4440,
    avg_uptime_pct: 99.6,
    avg_latency_ms: 24,
    avg_packet_loss_pct: 0.3,
    avg_throughput_mbps: 412,
    total_incidents: 9,
    open_events: 3,
    open_event_rate_pct: 0.7,
    isp_count: 3,
    sla_target_uptime_pct: 99.5,
    sla_met_pct: 91.7,
    sla_breach_days: 4,
    incident_rate_per_100_device_days: 0.2,
  },
  severity_distribution: [
    { severity: 'Critical', count: 6, pct_of_events: 1.5 },
    { severity: 'Major', count: 38, pct_of_events: 9.2 },
    { severity: 'Minor', count: 121, pct_of_events: 29.4 },
    { severity: 'Info', count: 247, pct_of_events: 59.9 },
  ],
  site_snapshot_30d: [
    { site_code: 'PRA', site_name: 'Poplar Ridge Apartments', isp_primary: 'Comcast Business', isp_secondary: 'AT&T Fiber', sla_target_uptime_pct: 99.5, sla_met_pct: 100, sla_breach_days: 0, avg_uptime_pct: 99.9, avg_latency_ms: 18, avg_packet_loss_pct: 0.1, incidents: 0 },
    { site_code: 'CYF', site_name: 'Cooper-Young Flats', isp_primary: 'AT&T Fiber', sla_target_uptime_pct: 99.5, sla_met_pct: 96.7, sla_breach_days: 1, avg_uptime_pct: 99.5, avg_latency_ms: 26, avg_packet_loss_pct: 0.4, incidents: 2 },
    { site_code: 'GTC', site_name: 'Germantown Commons', isp_primary: 'Comcast Business', sla_target_uptime_pct: 99.5, sla_met_pct: 100, sla_breach_days: 0, avg_uptime_pct: 99.8, avg_latency_ms: 21, avg_packet_loss_pct: 0.2, incidents: 1 },
    { site_code: 'BSL', site_name: 'Bartlett Station Lofts', isp_primary: 'Spectrum Business', isp_secondary: 'AT&T Fiber', sla_target_uptime_pct: 99.5, sla_met_pct: 90.0, sla_breach_days: 3, avg_uptime_pct: 99.1, avg_latency_ms: 34, avg_packet_loss_pct: 0.8, incidents: 4 },
    { site_code: 'MTC', site_name: 'Midtown Crossing', isp_primary: 'AT&T Fiber', sla_target_uptime_pct: 99.5, sla_met_pct: 100, sla_breach_days: 0, avg_uptime_pct: 99.7, avg_latency_ms: 23, avg_packet_loss_pct: 0.3, incidents: 2 },
  ],
  monthly_trend: [
    { month: '2026-07', avg_uptime_pct: 99.6, avg_latency_ms: 24, avg_packet_loss_pct: 0.3, incidents: 1 },
    { month: '2026-06', avg_uptime_pct: 99.5, avg_latency_ms: 25, avg_packet_loss_pct: 0.4, incidents: 3 },
    { month: '2026-05', avg_uptime_pct: 99.7, avg_latency_ms: 22, avg_packet_loss_pct: 0.2, incidents: 2 },
    { month: '2026-04', avg_uptime_pct: 99.4, avg_latency_ms: 27, avg_packet_loss_pct: 0.5, incidents: 4 },
    { month: '2026-03', avg_uptime_pct: 99.6, avg_latency_ms: 24, avg_packet_loss_pct: 0.3, incidents: 2 },
    { month: '2026-02', avg_uptime_pct: 99.8, avg_latency_ms: 20, avg_packet_loss_pct: 0.2, incidents: 1 },
  ],
}
