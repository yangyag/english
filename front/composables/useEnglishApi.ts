import type { CalendarOut, DayOut, ProgressOut, SubmitIn, TodayOut } from '~/types/api'
import { FetchError } from 'ofetch'

export class ApiError extends Error {
  constructor(public status: number, public detail: string) { super(detail) }
}
export function useEnglishApi() {
  async function request<T>(url: string, body?: SubmitIn): Promise<T> {
    try {
      return await $fetch<T>(url, body ? { method: 'POST', body, retry: 0 } : {}) as T
    } catch (error) {
      const e = error as FetchError
      throw new ApiError(e.statusCode ?? 0, typeof e.data?.detail === 'string' ? e.data.detail : '연결을 확인하고 다시 시도해 주세요.')
    }
  }
  return {
    getToday: () => request<TodayOut>('/v1/today'),
    getProgress: () => request<ProgressOut>('/v1/progress'),
    getCalendar: (month: string) => request<CalendarOut>(`/v1/calendar?month=${month}`),
    getDay: (day: string) => request<DayOut>(`/v1/calendar/${day}`),
    submit: (kind: 'new' | 'review', body: SubmitIn) => request<TodayOut>(`/v1/today/${kind}`, body),
  }
}
