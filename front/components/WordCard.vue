<script setup lang="ts">
import type { WordOut } from '~/types/api'

const props = defineProps<{
  word: WordOut
  flipped: boolean
}>()

const emit = defineEmits<{
  flip: []
}>()

type Chunk = { text: string; hit: boolean }

const exampleChunks = computed<Chunk[]>(() => {
  const example = props.word.example
  const needle = props.word.word.trim()
  if (!needle) return [{ text: example, hit: false }]
  const escaped = needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const re = new RegExp(`\\b(${escaped})\\b`, 'gi')
  const chunks: Chunk[] = []
  let last = 0
  let match = re.exec(example)
  while (match) {
    if (match.index > last) {
      chunks.push({ text: example.slice(last, match.index), hit: false })
    }
    chunks.push({ text: match[0], hit: true })
    last = match.index + match[0].length
    if (match[0].length === 0) re.lastIndex += 1
    match = re.exec(example)
  }
  if (last < example.length) {
    chunks.push({ text: example.slice(last), hit: false })
  }
  return chunks.length ? chunks : [{ text: example, hit: false }]
})
</script>

<template>
  <button
    class="card"
    type="button"
    :aria-pressed="props.flipped"
    :aria-label="props.flipped ? '카드 앞면으로' : '카드 뒤집기'"
    @click="emit('flip')"
  >
    <div v-if="!props.flipped" class="face front">
      <span class="rank">{{ props.word.rank }}</span>
      <p class="term">{{ props.word.word }}</p>
      <p class="hint">탭해서 뜻을 봅니다</p>
    </div>
    <div v-else class="face back">
      <span class="rank">{{ props.word.rank }}</span>
      <p class="term small">{{ props.word.word }}</p>
      <p class="meaning">{{ props.word.meaning }}</p>
      <p class="example">
        <template v-for="(chunk, i) in exampleChunks" :key="i">
          <mark v-if="chunk.hit" class="hit">{{ chunk.text }}</mark><template v-else>{{ chunk.text }}</template>
        </template>
      </p>
    </div>
  </button>
</template>

<style scoped>
.card {
  display: block;
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
  overflow: hidden;
}
.face {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  min-height: 280px;
  padding: 36px 24px 28px;
  border-radius: 18px;
  position: relative;
  box-shadow: 0 18px 40px rgba(28, 25, 20, 0.18);
}
.front {
  background: #1e2a24;
  color: #f4efe4;
}
.back {
  background: #faf6ee;
  color: #1c1914;
  border: 1px solid #e4dccb;
}
.rank {
  position: absolute;
  top: 16px;
  left: 18px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.04em;
  opacity: 0.7;
}
.term {
  margin: 0;
  max-width: 100%;
  font-family: Georgia, 'Palatino Linotype', Palatino, serif;
  font-size: clamp(2rem, 8vw, 3.2rem);
  line-height: 1.15;
  text-align: center;
  overflow-wrap: anywhere;
}
.term.small {
  font-size: 1.35rem;
  margin-bottom: 12px;
}
.hint {
  position: absolute;
  bottom: 18px;
  margin: 0;
  font-size: 13px;
  opacity: 0.65;
}
.meaning {
  margin: 0 0 16px;
  max-width: 100%;
  font-size: 1.35rem;
  font-weight: 700;
  text-align: center;
  line-height: 1.4;
  overflow-wrap: anywhere;
}
.example {
  margin: 0;
  max-width: 100%;
  font-size: 0.98rem;
  line-height: 1.55;
  text-align: center;
  color: #5b5348;
  font-style: italic;
  overflow-wrap: anywhere;
}
.hit {
  margin: 0;
  padding: 0 2px;
  border-radius: 3px;
  background: #f3d2b3;
  color: #9b2c22;
  font-weight: 700;
  font-style: italic;
}
</style>
