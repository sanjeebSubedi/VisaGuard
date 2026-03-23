import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'

type UserContextValue = {
  userId: string
  setUserId: (value: string) => void
}

const UserContext = createContext<UserContextValue | null>(null)

export function UserProvider({ children }: { children: ReactNode }) {
  const [userId, setUserId] = useState('user0')
  const value = useMemo(() => ({ userId, setUserId }), [userId])

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>
}

export function useUserContext() {
  const value = useContext(UserContext)
  if (!value) {
    throw new Error('useUserContext must be used within UserProvider')
  }
  return value
}
