/** Shared enums mirroring backend src/constants/enums.py (single source of truth on the wire). */
export const ROLES = ['engineer', 'analyst', 'viewer'] as const
export type RoleEnum = (typeof ROLES)[number]

export const JOB_STATUSES = ['pending', 'running', 'completed', 'failed'] as const
export type JobStatusEnum = (typeof JOB_STATUSES)[number]

export const GRID_CHOICES = [1, 5, 60] as const
export type GridChoice = (typeof GRID_CHOICES)[number]

export const AGG_STRATEGIES = ['mean', 'last', 'linear'] as const
export type AggStrategyEnum = (typeof AGG_STRATEGIES)[number]

export const FILL_STRATEGIES = ['locf', 'linear', 'seasonal_naive'] as const
export type FillStrategyEnum = (typeof FILL_STRATEGIES)[number]

export const GAP_SEVERITIES = ['low', 'medium', 'high'] as const
export type GapSeverityEnum = (typeof GAP_SEVERITIES)[number]

export const SOURCE_PROTOCOLS = ['opcua', 'dcs', 'csv'] as const
export type SourceProtocolEnum = (typeof SOURCE_PROTOCOLS)[number]

export const WINDOW_PRESETS = [
  { label: '近 2 小时', hours: 2 },
  { label: '近 6 小时', hours: 6 },
  { label: '近 12 小时', hours: 12 },
  { label: '近 24 小时', hours: 24 },
] as const
