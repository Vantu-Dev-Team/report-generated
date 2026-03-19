import { signInWithRedirect, signOut, fetchAuthSession, getCurrentUser as amplifyGetCurrentUser } from 'aws-amplify/auth'

export async function loginWithGoogle() {
  await signInWithRedirect({ provider: 'Google' })
}

export async function logout() {
  await signOut()
}

export async function getIdToken() {
  const session = await fetchAuthSession()
  return session.tokens?.idToken?.toString() || null
}

export async function getCurrentUser() {
  try {
    return await amplifyGetCurrentUser()
  } catch {
    return null
  }
}
