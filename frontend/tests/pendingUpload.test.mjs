import test from 'node:test'
import assert from 'node:assert/strict'

import {
  clearPendingUpload,
  getPendingUpload,
  setPendingUpload,
} from '../src/store/pendingUpload.js'

test('pendingUpload persists optional external research controls', () => {
  clearPendingUpload()

  setPendingUpload(
    ['brief.pdf'],
    'Simulate likely customer response',
    {
      researchEnabled: true,
      researchQuery: 'recent customer-service policy changes'
    }
  )

  assert.deepEqual(getPendingUpload(), {
    files: ['brief.pdf'],
    simulationRequirement: 'Simulate likely customer response',
    researchEnabled: true,
    researchQuery: 'recent customer-service policy changes',
    isPending: true
  })
})

test('clearPendingUpload resets external research controls', () => {
  setPendingUpload(
    ['brief.pdf'],
    'Simulate likely customer response',
    {
      researchEnabled: true,
      researchQuery: 'recent customer-service policy changes'
    }
  )

  clearPendingUpload()

  assert.deepEqual(getPendingUpload(), {
    files: [],
    simulationRequirement: '',
    researchEnabled: false,
    researchQuery: '',
    isPending: false
  })
})
