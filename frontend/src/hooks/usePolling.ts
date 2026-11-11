import { onBeforeUnmount, ref } from 'vue'

export function usePolling(intervalMs = 1500) {
  const active = ref(false)
  let timer: ReturnType<typeof setInterval> | null = null

  function stop() {
    active.value = false
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  function start(task: () => Promise<boolean>) {
    stop()
    active.value = true
    timer = setInterval(async () => {
      try {
        const done = await task()
        if (done) stop()
      } catch {
        stop()
      }
    }, intervalMs)
  }

  onBeforeUnmount(stop)

  return { active, start, stop }
}
