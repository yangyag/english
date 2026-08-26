<script setup lang="ts">
import type { WordOut } from '~/types/api'

const props = defineProps<{
  word: WordOut
  flipped: boolean
}>()

const emit = defineEmits<{
  flip: []
}>()
</script>

<template>
  <button
    class="card"
    type="button"
    :class="{ flipped: props.flipped }"
    :aria-pressed="props.flipped"
    :aria-label="props.flipped ? '카드 앞면으로' : '카드 뒤집기'"
    @click="emit('flip')"
  >
    <div class="card-inner">
      <div class="face front">
        <span class="rank">{{ props.word.rank }}</span>
        <p class="term">{{ props.word.word }}</p>
        <p class="hint">탭해서 뜻을 봅니다</p>
      </div>
      <div class="face back">
        <span class="rank">{{ props.word.rank }}</span>
        <p class="term small">{{ props.word.word }}</p>
        <p class="meaning">{{ props.word.meaning }}</p>
        <p class="example">{{ props.word.example }}</p>
      </div>
    </div>
  </button>
</template>

<style scoped>
.card {
  display: block;
  width: 100%;
  height: 320px;
  padding: 0;
  border: 0;
  background: transparent;
  perspective: 1200px;
  cursor: pointer;
}
.card-inner {
  position: relative;
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
  transition: transform 0.45s ease;
}
.card.flipped .card-inner {
  transform: rotateY(180deg);
}
.face {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 28px 24px;
  border-radius: 18px;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
  box-shadow: 0 18px 40px rgba(28, 25, 20, 0.18);
}
.front {
  background: #1e2a24;
  color: #f4efe4;
}
.back {
  background: #faf6ee;
  color: #1c1914;
  transform: rotateY(180deg);
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
  font-family: Georgia, 'Palatino Linotype', Palatino, serif;
  font-size: clamp(2rem, 8vw, 3.2rem);
  line-height: 1.15;
  text-align: center;
  word-break: break-word;
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
  font-size: 1.35rem;
  font-weight: 700;
  text-align: center;
  line-height: 1.4;
}
.example {
  margin: 0;
  max-width: 36em;
  font-size: 0.98rem;
  line-height: 1.55;
  text-align: center;
  color: #5b5348;
  font-style: italic;
}
</style>
