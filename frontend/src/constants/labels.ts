import type { AggStrategyEnum, FillStrategyEnum, GapSeverityEnum, JobStatusEnum, RoleEnum } from './enums'

export const ROLE_LABELS: Record<RoleEnum, string> = {
  engineer: '数据工程师',
  analyst: '可靠性分析师',
  viewer: '车间主管',
}

export const JOB_STATUS_LABELS: Record<JobStatusEnum, string> = {
  pending: '排队中',
  running: '执行中',
  completed: '已完成',
  failed: '失败',
}

export const AGG_LABELS: Record<AggStrategyEnum, string> = {
  mean: '桶内均值 mean',
  last: '桶内末值 last',
  linear: '桶均值 + 线性插值 linear',
}

export const FILL_LABELS: Record<FillStrategyEnum, string> = {
  locf: '前值填充 LOCF',
  linear: '两侧线性插值 linear',
  seasonal_naive: '季节朴素 seasonal_naive',
}

export const SEVERITY_LABELS: Record<GapSeverityEnum, string> = {
  low: '低',
  medium: '中',
  high: '高',
}

export const PROTOCOL_LABELS: Record<string, string> = {
  opcua: 'OPC-UA',
  dcs: 'DCS 历史站',
  csv: 'CSV 导出',
}

export const GRID_LABELS: Record<number, string> = {
  1: '1 秒网格',
  5: '5 秒网格',
  60: '60 秒网格',
}
