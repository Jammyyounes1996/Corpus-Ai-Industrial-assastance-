/* Workspace Tab Types */
/* 
  TypeScript interfaces and constants for workspace navigation
*/

export interface WorkspaceTab {
  id: string
  label: string
  icon?: string
  isPlaceholder: boolean
  description?: string
}

export interface WorkspaceTabDefinition {
  id: string
  label: string
  icon: string
  isPlaceholder: boolean
  description: string
}