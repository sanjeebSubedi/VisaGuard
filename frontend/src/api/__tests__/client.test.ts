import { beforeEach, describe, expect, it, vi } from 'vitest'

import { uploadDocument } from '@/api/intake'
import { WORKFLOW_RUN_TIMEOUT_MS, runComplianceWorkflow } from '@/api/workflows'

const fetchMock = vi.fn()

describe('frontend api client', () => {
  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  it('uses the long timeout for the compliance workflow run', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ final_compliance_record: { overall_state: 'IN_STATUS' } }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    await runComplianceWorkflow({ userId: 'user0', evaluationDate: '2026-03-22' })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe('http://127.0.0.1:8000/api/workflows/compliance/run')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'POST' })
    expect(fetchMock.mock.calls[0][1].headers).toMatchObject({ 'Content-Type': 'application/json' })
    expect(fetchMock.mock.calls[0][1].timeoutMs).toBe(WORKFLOW_RUN_TIMEOUT_MS)
  })

  it('sends manual EAD values as JSON', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ document_type: 'ead' }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const { createManualEadEntry } = await import('@/api/intake')

    await createManualEadEntry({
      userId: 'user0',
      alienRegistrationNumber: 'A123456789',
      category: 'C03B',
      cardStartDate: '2026-01-01',
      cardEndDate: '2026-12-31',
      cardNumber: 'EAD123',
    })

    expect(fetchMock.mock.calls[0][0]).toBe('http://127.0.0.1:8000/api/intake/ead/manual')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'POST' })
    expect(fetchMock.mock.calls[0][1].headers).toMatchObject({ 'Content-Type': 'application/json' })
    expect(JSON.parse(String(fetchMock.mock.calls[0][1].body))).toEqual({
      user_id: 'user0',
      alien_registration_number: 'A123456789',
      category: 'C03B',
      card_start_date: '2026-01-01',
      card_end_date: '2026-12-31',
      card_number: 'EAD123',
    })
  })

  it('uses form data for document uploads', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ document_type: 'i20' }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    await uploadDocument({
      userId: 'user0',
      documentType: 'i20',
      file: new File(['i20'], 'i20.pdf', { type: 'application/pdf' }),
    })

    expect(fetchMock.mock.calls[0][0]).toBe('http://127.0.0.1:8000/api/intake/documents')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'POST' })
    expect(fetchMock.mock.calls[0][1].body).toBeInstanceOf(FormData)
  })
})
