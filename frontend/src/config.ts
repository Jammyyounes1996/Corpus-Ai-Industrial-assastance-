// Configuration file for the React frontend
const backendBaseUrl = import.meta.env.VITE_BACKEND_BASE_URL || ''

export const config = {
  backendBaseUrl,
  
  // Chat API endpoints (relative paths for Vite proxy)
  chatEndpoints: {
    createChat: '/api/chats',
    streamChat: '/api/chat/:chatId/stream',
    ingestPdf: '/api/ingest/pdf',
    ingestAudio: '/api/ingest/audio', 
    ingestImage: '/api/ingest/image',
    health: '/health'
  },
  
  fileEndpoints: {
    listFiles: '/api/files',
    fileContent: '/api/files/:fileId/content',
    deleteFile: '/api/files/:fileId',
  },

  evaluationEndpoints: {
    evaluate: '/api/evaluate',
    evaluations: '/api/evaluations',
  },

  app: {
    title: 'CORPUS',
    maxSources: 3, // Maximum sources to show in UI
    supportedFiles: {
      pdf: ['application/pdf'],
      audio: ['audio/mpeg', 'audio/wav', 'audio/ogg'],
      image: ['image/jpeg', 'image/png', 'image/webp']
    }
  }
}