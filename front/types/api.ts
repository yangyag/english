export interface WordOut { rank: number; word: string; meaning: string; example: string; example_ko: string }
export interface TodayOut {
  date: string; new: WordOut[]; review: WordOut[]; review_source_date: string | null
  review_total: number; review_completed: number
  new_count: number; review_count: number
}
export interface WordResultIn { rank: number; known: boolean | null }
export interface SubmitIn { request_id: string; study_date: string; source_date: string | null; results: WordResultIn[] }
export interface ProgressOut {
  total_words: number; learned_count: number; next_rank: number; last_study_date: string | null
  study_days: number; undated_learned_count: number
}
export interface CalendarDay { date: string; new_count: number; review_count: number }
export interface CalendarOut { month: string; days: CalendarDay[] }
export interface DayOut { date: string; results: (WordOut & { kind: 'new' | 'review'; known: boolean | null })[] }
