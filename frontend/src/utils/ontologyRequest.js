export function buildOntologyFormData(pendingUpload, FormDataCtor = FormData) {
  const formData = new FormDataCtor()

  const files = pendingUpload?.files || []
  files.forEach(file => {
    formData.append('files', file)
  })

  formData.append('simulation_requirement', pendingUpload?.simulationRequirement || '')

  if (pendingUpload?.researchEnabled) {
    formData.append('research_enabled', 'true')

    const trimmedQuery = (pendingUpload?.researchQuery || '').trim()
    if (trimmedQuery) {
      formData.append('research_query', trimmedQuery)
    }
  }

  return formData
}
