import { parseSSEFrame, createChatStreamParser } from './chatStreamParser'

describe('Chat Stream Parser', () => {
  describe('parseSSEFrame', () => {
    it('should parse complete frames correctly', () => {
      const chunk = `event: token
data: {"token": "Hello", "message_id": "msg1"}

event: done
data: {"message_id": "msg1", "chat_id": "chat1"}

`
      const result = parseSSEFrame(chunk)
      
      expect(result.events).toHaveLength(2)
      expect(result.events[0]).toEqual({
        event: 'token',
        data: { token: 'Hello', message_id: 'msg1' }
      })
      expect(result.events[1]).toEqual({
        event: 'done',
        data: { message_id: 'msg1', chat_id: 'chat1' }
      })
      expect(result.buffer).toBe('')
    })

    it('should handle split chunks correctly', () => {
      const chunk1 = `event: token
data: {"token": "Hel`
      const chunk2 = `lo", "message_id": "msg1"}

event: done
data: {"message_id": "msg1", "chat_id": "chat1"}`
      
      // First chunk
      let result = parseSSEFrame(chunk1)
      expect(result.events).toHaveLength(0)
      expect(result.buffer).toBe('event: token\ndata: {"token": "Hel')
      
      // Second chunk with buffer
      result = parseSSEFrame(chunk2, result.buffer)
      expect(result.events).toHaveLength(2)
      expect(result.events[0]).toEqual({
        event: 'token',
        data: { token: 'Hello', message_id: 'msg1' }
      })
      expect(result.events[1]).toEqual({
        event: 'done',
        data: { message_id: 'msg1', chat_id: 'chat1' }
      })
      expect(result.buffer).toBe('')
    })

    it('should handle multiple frames in one chunk', () => {
      const chunk = `event: token
data: {"token": "Hello", "message_id": "msg1"}

event: token
data: {"token": " World", "message_id": "msg1"}

event: done
data: {"message_id": "msg1", "chat_id": "chat1"}`
      
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(3)
      expect(result.events[0]).toEqual({
        event: 'token',
        data: { token: 'Hello', message_id: 'msg1' }
      })
      expect(result.events[1]).toEqual({
        event: 'token',
        data: { token: ' World', message_id: 'msg1' }
      })
      expect(result.events[2]).toEqual({
        event: 'done',
        data: { message_id: 'msg1', 'chat_id': 'chat1' }
      })
    })

    it('should handle multi-line data correctly', () => {
      const chunk = `event: thinking_step
data: {"type": "reasoning", "content": "Let me think\\nabout this", "timestamp": "2024-01-01T00:00:00Z", "step_id": "step1"}

`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(1)
      expect(result.events[0]).toEqual({
        event: 'thinking_step',
        data: {
          type: 'reasoning',
          content: 'Let me think\nabout this',
          timestamp: '2024-01-01T00:00:00Z',
          step_id: 'step1'
        }
      })
    })

    it('should skip empty frames', () => {
      const chunk = `


event: token
data: {"token": "Hello", "message_id": "msg1"}


event: done
data: {"message_id": "msg1", "chat_id": "chat1"}


`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(2)
      expect(result.buffer).toBe('')
    })

    it('should preserve incomplete frames in buffer', () => {
      const chunk = `event: token
data: {"token": "Hel`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(0)
      expect(result.buffer).toBe('event: token\ndata: {"token": "Hel')
    })
  })

  describe('createChatStreamParser', () => {
    it('should parse chunks with state management', () => {
      const parser = createChatStreamParser()
      
      // First chunk (incomplete)
      const chunk1 = `event: token
data: {"token": "Hel`
      const events1 = parser.parse(chunk1)
      expect(events1).toHaveLength(0)
      expect(parser.getBuffer()).toBe('event: token\ndata: {"token": "Hel')
      
      // Second chunk (complete)
      const chunk2 = `lo", "message_id": "msg1"}

event: done
data: {"message_id": "msg1", "chat_id": "chat1"}`
      const events2 = parser.parse(chunk2)
      expect(events2).toHaveLength(2)
      expect(events2[0]).toEqual({
        event: 'token',
        data: { token: 'Hello', message_id: 'msg1' }
      })
      expect(events2[1]).toEqual({
        event: 'done',
        data: { message_id: 'msg1', chat_id: 'chat1' }
      })
      expect(parser.getBuffer()).toBe('')
    })

    it('should reset parser state', () => {
      const parser = createChatStreamParser()
      
      // Parse some data
      parser.parse(`event: token
data: {"token": "Hello", "message_id": "msg1"}`)
      expect(parser.getBuffer()).toBe('')
      
      // Reset should clear buffer
      parser.reset()
      expect(parser.getBuffer()).toBe('')
    })
  })

  describe('Event validation', () => {
    it('should accept valid token events', () => {
      const chunk = `event: token
data: {"token": "Hello", "message_id": "msg1"}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(1)
      expect(result.events[0]).toEqual({
        event: 'token',
        data: { token: 'Hello', message_id: 'msg1' }
      })
    })

    it('should reject invalid token events', () => {
      const chunk = `event: token
data: {"token": "", "message_id": "msg1"}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(0) // Invalid events are filtered out
    })

    it('should accept valid thinking_step events', () => {
      const chunk = `event: thinking_step
data: {"type": "reasoning", "content": "Thinking", "timestamp": "2024-01-01T00:00:00Z", "step_id": "step1"}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(1)
      expect(result.events[0]).toEqual({
        event: 'thinking_step',
        data: {
          type: 'reasoning',
          content: 'Thinking',
          timestamp: '2024-01-01T00:00:00Z',
          step_id: 'step1'
        }
      })
    })

    it('should reject invalid thinking_step events', () => {
      const chunk = `event: thinking_step
data: {"content": "Thinking", "timestamp": "2024-01-01T00:00:00Z", "step_id": "step1"}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(0) // Invalid events are filtered out
    })

    it('should accept backend thinking_step types', () => {
      const chunk = `event: thinking_step
data: {"type": "router", "content": "Routing", "timestamp": "2024-01-01T00:00:00Z", "step_id": "step1"}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(1)
      expect(result.events[0]).toEqual({
        event: 'thinking_step',
        data: {
          type: 'router',
          content: 'Routing',
          timestamp: '2024-01-01T00:00:00Z',
          step_id: 'step1'
        }
      })
    })

    it('should accept valid thinking delta events', () => {
      const chunk = `event: thinking_delta
data: {"delta": "Searching", "elapsed_ms": 1200}

event: thinking_delta
data: {"delta": " more", "elapsed_ms": 1500}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(2)
      expect(result.events[0]).toMatchObject({
        event: 'thinking_delta',
        data: {
          delta: 'Searching',
          elapsed_ms: 1200
        }
      })
      expect(result.events[1]).toMatchObject({
        event: 'thinking_delta',
        data: {
          delta: ' more',
          elapsed_ms: 1500
        }
      })
    })

    it('should accept valid sources events', () => {
      const chunk = `event: sources
data: {"message_id": "msg1", "sources": [{"file_id": "file1", "filename": "test.pdf", "file_type": "pdf", "chunk_index": 0, "excerpt": "Test content"}]}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(1)
      expect(result.events[0]).toEqual({
        event: 'sources',
        data: {
          message_id: 'msg1',
          sources: [{
            file_id: 'file1',
            filename: 'test.pdf',
            file_type: 'pdf',
            chunk_index: 0,
            excerpt: 'Test content'
          }]
        }
      })
    })

    it('should reject invalid sources events', () => {
      const chunk = `event: sources
data: {"message_id": "msg1", "sources": []}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(0) // Invalid events are filtered out
    })

    it('should accept sources events without message_id', () => {
      const chunk = `event: sources
data: {"sources": [{"file_id": "file1", "filename": "test.pdf", "file_type": "pdf", "chunk_index": 0, "excerpt": "Test content"}]}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(1)
      expect(result.events[0]).toEqual({
        event: 'sources',
        data: {
          sources: [{
            file_id: 'file1',
            filename: 'test.pdf',
            file_type: 'pdf',
            chunk_index: 0,
            excerpt: 'Test content'
          }]
        }
      })
    })

    it('should accept valid done events', () => {
      const chunk = `event: done
data: {"message_id": "msg1", "chat_id": "chat1"}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(1)
      expect(result.events[0]).toEqual({
        event: 'done',
        data: { message_id: 'msg1', chat_id: 'chat1' }
      })
    })

    it('should reject invalid done events', () => {
      const chunk = `event: done
data: {"message_id": "", "chat_id": "chat1"}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(0) // Invalid events are filtered out
    })

    it('should accept done event with numeric message_id', () => {
      const chunk = `event: done
data: {"message_id": 42, "chat_id": "chat1"}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(1)
      expect(result.events[0]).toEqual({
        event: 'done',
        data: { message_id: '42', chat_id: 'chat1' }
      })
    })

    it('should accept valid error events', () => {
      const chunk = `event: error
data: {"error": "Something went wrong", "code": "ERROR_CODE", "message_id": "msg1"}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(1)
      expect(result.events[0]).toEqual({
        event: 'error',
        data: {
          error: 'Something went wrong',
          code: 'ERROR_CODE',
          message_id: 'msg1'
        }
      })
    })

    it('should reject invalid error events', () => {
      const chunk = `event: error
data: {"error": ""}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(0) // Invalid events are filtered out
    })
  })

  describe('Malformed JSON handling', () => {
    it('should handle malformed JSON with error event', () => {
      const chunk = `event: token
data: {"token": "Hello", "message_id": "invalid json

event: done
      data: {"message_id": "msg1", "chat_id": "chat1"}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(2) // Error event is created and later valid frames still parse
      expect(result.events[0]).toEqual({
        event: 'error',
        data: {
          error: 'Failed to parse token event data: JSON parse error',
          code: 'INVALID_JSON'
        }
      })
      expect(result.events[1]).toEqual({
        event: 'done',
        data: { message_id: 'msg1', chat_id: 'chat1' }
      })
    })

    it('should handle plain text data', () => {
      const chunk = `event: token
data: plain text token

event: done
data: {"message_id": "msg1", "chat_id": "chat1"}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(2)
      expect(result.events[0]).toEqual({
        event: 'token',
        data: { token: 'plain text token' }
      })
      expect(result.events[1]).toEqual({
        event: 'done',
        data: { message_id: 'msg1', chat_id: 'chat1' }
      })
    })
  })

  describe('Unknown events', () => {
    it('should ignore unknown events safely', () => {
      const chunk = `event: unknown_event
data: {"some": "data"}

event: token
data: {"token": "Hello", "message_id": "msg1"}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(1)
      expect(result.events[0]).toEqual({
        event: 'token',
        data: { token: 'Hello', message_id: 'msg1' }
      })
    })

    it('should handle mixed known and unknown events', () => {
      const chunk = `event: unknown1
data: {"data": "value1"}

event: token
data: {"token": "Hello", "message_id": "msg1"}

event: unknown2
data: {"data": "value2"}

event: done
data: {"message_id": "msg1", "chat_id": "chat1"}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(2)
      expect(result.events[0]).toEqual({
        event: 'token',
        data: { token: 'Hello', message_id: 'msg1' }
      })
      expect(result.events[1]).toEqual({
        event: 'done',
        data: { message_id: 'msg1', chat_id: 'chat1' }
      })
    })
  })

  describe('Edge cases', () => {
    it('should handle empty string chunk', () => {
      const result = parseSSEFrame('')
      expect(result.events).toHaveLength(0)
      expect(result.buffer).toBe('')
    })

    it('should handle whitespace-only chunk', () => {
      const result = parseSSEFrame('   \n   \n   ')
      expect(result.events).toHaveLength(0)
      expect(result.buffer).toBe('   \n   \n   ')
    })

    it('should handle malformed SSE format gracefully', () => {
      const chunk = `this is not a proper sse format
event: missing data line

event: token
data: {"token": "Hello", "message_id": "msg1"}`
      const result = parseSSEFrame(chunk)
      expect(result.events).toHaveLength(1)
      expect(result.events[0]).toEqual({
        event: 'token',
        data: { token: 'Hello', message_id: 'msg1' }
      })
    })

    it('should handle non-string inputs safely', () => {
      // @ts-expect-error - testing runtime behavior
      const result = parseSSEFrame(null, undefined)
      expect(result.events).toHaveLength(0)
      expect(result.buffer).toBe('')
    })
  })
})
