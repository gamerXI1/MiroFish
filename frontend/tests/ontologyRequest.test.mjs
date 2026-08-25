import test from 'node:test'
import assert from 'node:assert/strict'

import { buildOntologyFormData } from '../src/utils/ontologyRequest.js'

class FakeFormData {
  constructor() {
    this.entries = []
  }

  append(key, value) {
    this.entries.push([key, value])
  }
}

test('buildOntologyFormData omits external research fields when research is disabled', () => {
  const formData = buildOntologyFormData(
    {
      files: ['doc-a.pdf', 'doc-b.md'],
      simulationRequirement: 'Model how the narrative evolves',
      researchEnabled: false,
      researchQuery: 'ignored query'
    },
    FakeFormData
  )

  assert.deepEqual(formData.entries, [
    ['files', 'doc-a.pdf'],
    ['files', 'doc-b.md'],
    ['simulation_requirement', 'Model how the narrative evolves']
  ])
})

test('buildOntologyFormData includes explicit research fields when research is enabled', () => {
  const formData = buildOntologyFormData(
    {
      files: ['seed.txt'],
      simulationRequirement: 'Assess likely market reaction',
      researchEnabled: true,
      researchQuery: ' latest market commentary '
    },
    FakeFormData
  )

  assert.deepEqual(formData.entries, [
    ['files', 'seed.txt'],
    ['simulation_requirement', 'Assess likely market reaction'],
    ['research_enabled', 'true'],
    ['research_query', 'latest market commentary']
  ])
})

test('buildOntologyFormData defaults research query to omission when enabled but blank', () => {
  const formData = buildOntologyFormData(
    {
      files: ['seed.txt'],
      simulationRequirement: 'Assess likely market reaction',
      researchEnabled: true,
      researchQuery: '   '
    },
    FakeFormData
  )

  assert.deepEqual(formData.entries, [
    ['files', 'seed.txt'],
    ['simulation_requirement', 'Assess likely market reaction'],
    ['research_enabled', 'true']
  ])
})
