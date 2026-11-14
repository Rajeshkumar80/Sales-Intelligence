export class ApiError extends Error {
  code: string
  status: number
  fields: { field: string; message: string }[]

  constructor(status: number, code: string, message: string, fields: { field: string; message: string }[] = []) {
    super(message)
    this.status = status
    this.code = code
    this.fields = fields
  }
}

export type Query = Record<string, string | number | boolean | null | undefined>

export function qs(params: Query = {}): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  })
  const text = search.toString()
  return text ? `?${text}` : ''
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: init?.body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    let code = `HTTP_${response.status}`
    let message = response.statusText || 'Request failed'
    let fields: { field: string; message: string }[] = []
    try {
      const body = await response.json()
      if (body?.detail?.message) {
        message = body.detail.message
        code = body.detail.code ?? code
        fields = body.detail.fields ?? []
      } else if (typeof body?.detail === 'string') {
        message = body.detail
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, code, message, fields)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export function downloadCsv(path: string, filename: string): void {
  const anchor = document.createElement('a')
  anchor.href = path
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}
