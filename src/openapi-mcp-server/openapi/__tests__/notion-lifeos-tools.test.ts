import { describe, it, expect } from 'vitest'
import path from 'path'
import fs from 'fs'
import type { OpenAPIV3 } from 'openapi-types'
import { OpenAPIToMCPConverter } from '../parser'

describe('Life OS tool additions', () => {
  const spec = JSON.parse(
    fs.readFileSync(path.resolve(process.cwd(), 'scripts/notion-openapi.json'), 'utf-8')
  ) as OpenAPIV3.Document
  const { tools, openApiLookup } = new OpenAPIToMCPConverter(spec).convertToMCPTools()
  const methods = Object.values(tools).flatMap((t) => t.methods)

  const expected: Array<[string, string]> = [
    ['API-list-views', 'get /v1/views'],
    ['API-create-view', 'post /v1/views'],
    ['API-retrieve-a-view', 'get /v1/views/{view_id}'],
    ['API-update-a-view', 'patch /v1/views/{view_id}'],
    ['API-delete-view', 'delete /v1/views/{view_id}'],
    ['API-create-view-query', 'post /v1/views/{view_id}/queries'],
    ['API-get-view-query-results', 'get /v1/views/{view_id}/queries/{query_id}'],
    ['API-delete-view-query', 'delete /v1/views/{view_id}/queries/{query_id}'],
    ['API-create-database', 'post /v1/databases'],
    ['API-update-a-database', 'patch /v1/databases/{database_id}'],
    ['API-list-comments', 'get /v1/comments'],
    ['API-retrieve-comment-by-id', 'get /v1/comments/{comment_id}'],
    ['API-update-a-comment', 'patch /v1/comments/{comment_id}'],
    ['API-delete-a-comment', 'delete /v1/comments/{comment_id}'],
  ]

  it('exposes every Life OS tool', () => {
    expect(methods.map((m) => m.name)).toEqual(expect.arrayContaining(expected.map(([n]) => n.replace(/^API-/, ''))))
  })

  it('maps each tool to the expected method and path', () => {
    for (const [name, target] of expected) {
      const entry = Object.values(openApiLookup).find((op) => op.operationId === name.replace(/^API-/, ''))
      expect(entry, name).toBeDefined()
      expect(`${entry?.method} ${entry?.path}`, name).toBe(target)
    }
  })

  it('declares the version header on comment creation and accepts position', () => {
    const createComment = spec.paths['/v1/comments']?.post
    expect(JSON.stringify(createComment?.parameters)).toContain('#/components/parameters/notionVersion')
    const patchChildren = spec.paths['/v1/blocks/{block_id}/children']?.patch
    const properties = (patchChildren as any)?.requestBody?.content?.['application/json']?.schema?.properties
    expect(properties).toHaveProperty('position')
  })

  it('defaults Notion-Version to 2026-03-11', () => {
    expect((spec.components?.parameters?.notionVersion as any)?.schema?.default).toBe('2026-03-11')
  })
})
