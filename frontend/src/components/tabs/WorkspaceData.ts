import type { LucideIcon } from 'lucide-react'
import { MessageCircle, FileText, Camera, BarChart, Wrench } from 'lucide-react'

interface WorkspaceTabDefinition {
  id: string
  label: string
  icon: LucideIcon
  isPlaceholder: boolean
  description: string
}

export const WORKSPACE_TABS: WorkspaceTabDefinition[] = [
  {
    id: 'chat',
    label: 'Chat',
    icon: MessageCircle,
    isPlaceholder: false,
    description: 'Converse with the AI assistant about industrial processes'
  },
  {
    id: 'documents',
    label: 'Documents',
    icon: FileText,
    isPlaceholder: false,
    description: 'Upload and manage your industrial documents and manuals'
  },
  {
    id: 'ocr',
    label: 'OCR',
    icon: Camera,
    isPlaceholder: false,
    description: 'Extract text from images of equipment labels and gauges'
  },
  {
    id: 'analysis',
    label: 'Analysis',
    icon: BarChart,
    isPlaceholder: false,
    description: 'Analyze industrial data and generate insights'
  },
  {
    id: 'tools',
    label: 'Tools',
    icon: Wrench,
    isPlaceholder: false,
    description: 'Access industrial tools and calculators'
  }
]