export const queryKeys = {
  snapshot: (userId: string) => ['snapshot', userId] as const,
  reviewItems: (userId: string) => ['review-items', userId] as const,
  workflowResult: (userId: string) => ['workflow-result', userId] as const,
}
