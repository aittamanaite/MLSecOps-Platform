
export interface FlowItem {
  flow_duration: number
  total_fwd_packets: number
  total_backward_packets: number
  total_length_of_fwd_packets: number
  total_length_of_bwd_packets: number
  fwd_packet_length_max: number
  fwd_packet_length_min: number
  fwd_packet_length_mean: number
  fwd_packet_length_std: number
  bwd_packet_length_max: number
  bwd_packet_length_min: number
  bwd_packet_length_mean: number
  bwd_packet_length_std: number
  flow_iat_mean: number
  flow_iat_std: number
  flow_iat_max: number
  flow_iat_min: number
  fwd_iat_total: number
  fwd_iat_mean: number
  fwd_iat_std: number
  bwd_iat_total: number
  bwd_iat_mean: number
  bwd_iat_std: number
  fin_flag_count: number
  syn_flag_count: number
  rst_flag_count: number
  psh_flag_count: number
  ack_flag_count: number
  average_packet_size: number
  active_mean: number
  active_std: number
  idle_mean: number
  idle_std: number
}

/** The 33 field names, grouped for the Inspector's accordion form. */
export const FLOW_FIELD_GROUPS: { label: string; fields: (keyof FlowItem)[] }[] = [
  {
    label: 'Forward packets',
    fields: [
      'total_fwd_packets',
      'total_length_of_fwd_packets',
      'fwd_packet_length_max',
      'fwd_packet_length_min',
      'fwd_packet_length_mean',
      'fwd_packet_length_std',
    ],
  },
  {
    label: 'Backward packets',
    fields: [
      'total_backward_packets',
      'total_length_of_bwd_packets',
      'bwd_packet_length_max',
      'bwd_packet_length_min',
      'bwd_packet_length_mean',
      'bwd_packet_length_std',
    ],
  },
  {
    label: 'Timing (IAT)',
    fields: [
      'flow_iat_mean',
      'flow_iat_std',
      'flow_iat_max',
      'flow_iat_min',
      'fwd_iat_total',
      'fwd_iat_mean',
      'fwd_iat_std',
      'bwd_iat_total',
      'bwd_iat_mean',
      'bwd_iat_std',
    ],
  },
  {
    label: 'TCP flags',
    fields: ['fin_flag_count', 'syn_flag_count', 'rst_flag_count', 'psh_flag_count', 'ack_flag_count'],
  },
  {
    label: 'Activity',
    fields: ['active_mean', 'active_std', 'idle_mean', 'idle_std'],
  },
  {
    label: 'Flow',
    fields: ['flow_duration', 'average_packet_size'],
  },
]

/** Unit hints shown as input placeholders, per field. */
export const FIELD_UNITS: Partial<Record<keyof FlowItem, string>> = {
  flow_duration: 'microseconds',
  total_length_of_fwd_packets: 'bytes',
  total_length_of_bwd_packets: 'bytes',
  average_packet_size: 'bytes',
}


export interface PredictResponse {
  is_anomaly: 'ATTACK' | 'BENIGN'
  confidence: number
  [key: string]: unknown
}


export function isAttack(result: Pick<PredictResponse, 'is_anomaly'>): boolean {
  return String(result.is_anomaly).trim().toUpperCase() === 'ATTACK'
}

export interface BatchPredictResponse {
  predictions: PredictResponse[]
  total_processed: number
  anomalies_found: number
}
export interface HealthResponse {
  status: string
  model_loaded: boolean
  [key: string]: unknown
}

export class ApiError extends Error {
  status: number
  body: unknown

  constructor(message: string, status: number, body: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}
