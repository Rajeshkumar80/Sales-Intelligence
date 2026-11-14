export interface Kpis {
  total_revenue: number
  total_transactions: number
  total_products: number
  total_quantity: number
  average_order_value: number
}

export interface DailyPoint {
  date: string
  revenue: number
  quantity: number
  orders: number
}

export interface MonthlyPoint {
  month: string
  revenue: number
  quantity: number
  orders: number
}

export interface CategoryPoint {
  category: string
  revenue: number
  quantity: number
}

export interface RegionPoint {
  region: string
  revenue: number
  quantity: number
  orders: number
}

export interface ProductRow {
  product_id: string
  product_name: string
  revenue: number
  quantity: number
  orders: number
}

export interface Overview {
  has_data: boolean
  filters: Record<string, string | null>
  kpis: Kpis
  daily: DailyPoint[]
  monthly: MonthlyPoint[]
  category: CategoryPoint[]
  region: RegionPoint[]
  top_products: ProductRow[]
  all_products: ProductRow[]
}

export interface Transaction {
  transaction_id: string
  product_id: string
  product_name: string
  category: string
  quantity: number
  unit_price: number
  revenue: number
  region: string
  timestamp: string
  source: string
  processed: boolean
  batch_id: string | null
}

export interface Paged<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface JobStage {
  name: string
  status: string
  started_at: string | null
  finished_at: string | null
  details: Record<string, string | number>
}

export interface JobLog {
  ts: string
  level: string
  message: string
}

export interface Job {
  job_id: string
  batch_id: string
  status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED'
  batch_size: number
  started_at: string
  finished_at: string | null
  duration_ms: number | null
  stages: JobStage[]
  logs?: JobLog[]
  error: string | null
  metrics: Record<string, number>
  execution_mode: string
}

export interface Reconciliation {
  match: boolean
  tolerance: number
  mr_revenue: number
  hive_revenue: number
  delta_revenue: number
  mr_quantity: number
  hive_quantity: number
  mr_orders: number
  hive_orders: number
  products: number
}

export interface HiveRow {
  section: string
  key: string
  label: string
  revenue: number
  quantity: number
  orders: number
}

export interface Snapshot {
  batch_id: string
  job_id: string
  generated_at: string
  mr_counters: Record<string, number>
  hive_results: HiveRow[]
  reconciliation: Reconciliation
}

export interface Health {
  status: string
  components: {
    mongodb: { status: string; database?: string; collections?: string[]; transactions?: number; error?: string }
    hive: { status: string; url: string }
    hadoop: {
      hadoop_bin: string
      hadoop_bin_exists: boolean
      hdfs_bin_exists: boolean
      beeline_exists: boolean
      jar_built: boolean
    }
  }
  server_time: string
}

export interface Settings {
  batch_size: number
  simulator: { interval_seconds: number; batch_size: number }
  csv: { max_mb: number; max_rows: number }
  hive: { url: string; database: string }
  hdfs: { input: string; revenue: string }
  execution_mode: string
  infra: Health['components']['hadoop']
}

export interface SimulatorStatus {
  running: boolean
  interval_seconds: number
  batch_size: number
  generated: number
  ticks: number
  started_at: string | null
  last_error: string | null
}

export interface UploadReport {
  filename: string
  rows_total: number
  inserted: number
  duplicates: number
  invalid: number
  duplicate_details: { transaction_id: string; error: string }[]
  invalid_details: { row: number; error: string; raw: string | null }[]
  write_errors: { transaction_id: string; error: string }[]
}

export interface FilterOptions {
  regions: string[]
  categories: string[]
  products: { product_id: string; product_name: string }[]
  dates: string[]
}
