<template>
  <div class="login">
    <section class="login__left">
      <div class="login__brand">
        <span class="eyebrow">observatory log · 2026.11</span>
        <h1 class="display login__title">TSALIGN</h1>
        <p class="login__lede">
          工业时序遥测对齐与缺口修复工作台。<br />
          把三套采集网关的原始时间戳，校准成一张可复现的观测网格。
        </p>
      </div>

      <article class="login__plate">
        <div class="eyebrow">observation plate</div>
        <dl>
          <div><dt>客户</dt><dd>瀚川重工 · 常州注塑基地</dd></div>
          <div><dt>设备</dt><dd>注塑机 420 台 · 已接入 6 台 / 12 测点</dd></div>
          <div><dt>网关</dt><dd class="mono">GW-CHZ-01 / 02 / 03</dd></div>
          <div><dt>已知偏差</dt><dd class="mono">GW-CHZ-02 +312ms</dd></div>
        </dl>
        <div class="login__plate-line"></div>
        <p class="login__plate-note">
          对齐网格 1s / 5s / 60s · 填补 locf / linear / seasonal_naive · 每次运行生成质量分与缺口事件
        </p>
      </article>

      <footer class="login__foot mono">
        <span>lat 31.8107 N · lon 119.9741 E</span>
        <span>telescope 5.1m · logbook III</span>
      </footer>
    </section>

    <section class="login__right">
      <div class="login__form-wrap">
        <div class="eyebrow">sign in · 观测员登录</div>
        <h2 class="title login__form-title">进入对齐台</h2>
        <p class="login__hint">使用设备可靠性组账号登录，按角色进入对应页面。</p>

        <form class="login__form" @submit.prevent="submit">
          <label class="label">邮箱</label>
          <input v-model="email" class="input mono" type="email" autocomplete="username" placeholder="engineer@tsalign.demo" />
          <label class="label">密码</label>
          <input
            v-model="password"
            class="input mono"
            type="password"
            autocomplete="current-password"
            placeholder="Demo@2026"
          />
          <button class="btn btn-solid login__submit" type="submit" :disabled="auth.loading">
            {{ auth.loading ? '核对中…' : '登录' }}
          </button>
        </form>

        <ErrorNotice :error="error" />
        <p class="login__accounts mono">
          演示账号：engineer@tsalign.demo / analyst@tsalign.demo / viewer@tsalign.demo<br />
          统一密码：Demo@2026
        </p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import { useAuthStore } from '../stores/authStore'
import type { ApiError } from '../types/api'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const email = ref('engineer@tsalign.demo')
const password = ref('Demo@2026')
const error = ref<ApiError | null>(null)

async function submit() {
  error.value = null
  try {
    await auth.login(email.value.trim(), password.value)
    const target = typeof route.query.redirect === 'string' ? route.query.redirect : '/sources'
    await router.push(target)
  } catch (err) {
    error.value = err as ApiError
  }
}
</script>

<style scoped>
.login {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  min-height: 100vh;
}
.login__left {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: clamp(32px, 5vw, 72px);
  border-right: 1px solid var(--rule-strong);
  background:
    radial-gradient(circle at 22% 16%, oklch(0.9 0.05 78 / 0.5), transparent 45%),
    linear-gradient(to bottom, var(--paper-2), var(--paper));
  position: relative;
}
.login__left::after {
  content: '';
  position: absolute;
  inset: 26px 26px 26px auto;
  width: 1px;
  background-image: repeating-linear-gradient(
    to bottom,
    var(--rule-strong) 0,
    var(--rule-strong) 1px,
    transparent 1px,
    transparent 18px
  );
  opacity: 0.6;
}
.login__title {
  margin-top: 8px;
  letter-spacing: 0.05em;
  color: var(--ink-green);
}
.login__lede {
  max-width: 46ch;
  color: var(--ink-soft);
  margin: 14px 0 0;
}
.login__plate {
  margin-top: 44px;
  max-width: 380px;
  border: 1px solid var(--rule-strong);
  background: oklch(0.985 0.012 88 / 0.85);
  padding: 16px 18px 14px;
  transform: rotate(-0.6deg);
  box-shadow: 6px 8px 0 oklch(0.88 0.03 80 / 0.5);
}
.login__plate dl {
  margin: 10px 0 0;
  font-size: 11.5px;
}
.login__plate dl div {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 4px 0;
  border-bottom: 1px dotted var(--rule);
}
.login__plate dt {
  color: var(--ink-soft);
}
.login__plate dd {
  margin: 0;
  text-align: right;
}
.login__plate-line {
  height: 1px;
  background: var(--rule-strong);
  margin: 12px 0 8px;
}
.login__plate-note {
  font-size: 10.5px;
  color: var(--ink-soft);
  line-height: 1.8;
  margin: 0;
}
.login__foot {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--ink-faint);
  margin-top: 40px;
}
.login__right {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px clamp(24px, 4vw, 64px);
}
.login__form-wrap {
  width: 100%;
  max-width: 360px;
}
.login__form-title {
  margin-top: 6px;
}
.login__hint {
  color: var(--ink-soft);
  font-size: 12px;
  margin: 6px 0 22px;
}
.login__form {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.login__form .label {
  margin-top: 10px;
}
.login__submit {
  margin-top: 18px;
  justify-content: center;
}
.login__accounts {
  margin-top: 26px;
  font-size: 10.5px;
  line-height: 1.9;
  color: var(--ink-faint);
  border-top: 1px solid var(--rule);
  padding-top: 12px;
}
@media (max-width: 900px) {
  .login {
    grid-template-columns: 1fr;
  }
  .login__left {
    border-right: 0;
    border-bottom: 1px solid var(--rule-strong);
  }
}
</style>
