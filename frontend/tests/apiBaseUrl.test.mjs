import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const apiSource = readFileSync(new URL('../src/api/index.js', import.meta.url), 'utf8')
const viteSource = readFileSync(new URL('../vite.config.js', import.meta.url), 'utf8')

assert.match(apiSource, /baseURL:\s*import\.meta\.env\.VITE_API_BASE_URL\s*\|\|\s*''/)
assert.doesNotMatch(apiSource, /http:\/\/localhost:5001/)
assert.match(viteSource, /const\s+backendProxyTarget\s*=\s*process\.env\.VITE_BACKEND_PROXY_TARGET\s*\|\|\s*'http:\/\/127\.0\.0\.1:5001'/)
assert.match(viteSource, /target:\s*backendProxyTarget/)
assert.match(viteSource, /host:\s*'0\.0\.0\.0'/)
assert.match(viteSource, /strictPort:\s*true/)
assert.match(viteSource, /open:\s*false/)

console.log('ok')
