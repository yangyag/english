export type Phase = 'review' | 'new' | 'done'

export interface WordOut {
  rank: number
  word: string
  meaning: string
  example: string
}

export interface TodayOut {
  date: string
  phase: Phase
  review: WordOut[]
  new: WordOut[]
  review_done: boolean
  new_done: boolean
}

export interface WordResultIn {
  rank: number
  known: boolean
}

export interface SubmitIn {
  results: WordResultIn[]
}

export interface ProgressOut {
  total_words: number
  learned_count: number
  next_rank: number
  last_study_date: string | null
  streak_days: number
}
