import type { ProgressOut, SubmitIn, TodayOut, WordResultIn } from '~/types/api'
import { FetchError } from 'ofetch'

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

function unwrap(error: unknown): never {
  if (error instanceof ApiError) {
    throw error
  }
  if (error instanceof FetchError) {
    const detail =
      typeof error.data?.detail === 'string' ? error.data.detail : '요청에 실패했습니다.'
    throw new ApiError(error.statusCode ?? 0, detail)
  }
  throw new ApiError(0, '요청에 실패했습니다.')
}

export function useEnglishApi() {
  async function getToday(): Promise<TodayOut> {
    try {
      return await $fetch<TodayOut>('/v1/today')
    } catch (error) {
      unwrap(error)
    }
  }

  async function submitReview(results: WordResultIn[]): Promise<TodayOut> {
    const body: SubmitIn = { results }
    try {
      return await $fetch<TodayOut>('/v1/today/review', { method: 'POST', body })
    } catch (error) {
      unwrap(error)
    }
  }

  async function submitNew(results: WordResultIn[]): Promise<TodayOut> {
    const body: SubmitIn = { results }
    try {
      return await $fetch<TodayOut>('/v1/today/new', { method: 'POST', body })
    } catch (error) {
      unwrap(error)
    }
  }

  async function getExtra(): Promise<TodayOut> {
    try {
      return await $fetch<TodayOut>('/v1/today/extra')
    } catch (error) {
      unwrap(error)
    }
  }

  async function submitExtra(results: WordResultIn[]): Promise<TodayOut> {
    const body: SubmitIn = { results }
    try {
      return await $fetch<TodayOut>('/v1/today/extra', { method: 'POST', body })
    } catch (error) {
      unwrap(error)
    }
  }

  async function getProgress(): Promise<ProgressOut> {
    try {
      return await $fetch<ProgressOut>('/v1/progress')
    } catch (error) {
      unwrap(error)
    }
  }

  return { getToday, submitReview, submitNew, getExtra, submitExtra, getProgress }
}
