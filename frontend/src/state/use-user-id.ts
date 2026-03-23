import { useUserContext } from '@/state/user-context'

export function useUserId() {
  return useUserContext()
}
