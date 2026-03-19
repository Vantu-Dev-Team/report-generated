import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { fetchAuthSession } from 'aws-amplify/auth'
import { loginWithGoogle, logout as amplifyLogout, getCurrentUser } from './authService.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [authError, setAuthError] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const currentUser = await getCurrentUser()
      setUser(currentUser)

      // Detect failed OAuth callback (code in URL but no session)
      const hasCode = window.location.search.includes('code=')
      if (hasCode && !currentUser) {
        await amplifyLogout()
        setAuthError('Tu cuenta no tiene acceso autorizado.')
        setUser(null)
        return
      }

      if (currentUser) {
        // For Google (federated) users, email lives in the ID token payload
        try {
          const session = await fetchAuthSession()
          const payload = session.tokens?.idToken?.payload
          setEmail((payload?.email) || currentUser?.signInDetails?.loginId || '')
        } catch {
          setEmail(currentUser?.signInDetails?.loginId || '')
        }
      }
    } catch {
      setUser(null)
      setEmail('')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const login = useCallback(() => loginWithGoogle(), [])

  const logout = useCallback(async () => {
    await amplifyLogout()
    setUser(null)
    setEmail('')
  }, [])

  return (
    <AuthContext.Provider value={{ user, email, isLoading, authError, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
