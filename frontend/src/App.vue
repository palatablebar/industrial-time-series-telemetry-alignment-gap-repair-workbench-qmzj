<template>
  <AppShell v-if="!isPublic"><router-view /></AppShell>
  <router-view v-else />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppShell from './components/common/AppShell.vue'

const route = useRoute()
const isPublic = computed(() => Boolean(route.meta.public))
</script>
