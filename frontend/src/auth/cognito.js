import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
} from 'amazon-cognito-identity-js'

const USER_POOL_ID = 'us-east-1_OVlXl5RFG'
const CLIENT_ID = '3jghasft3af5uv5eukosn950pf'

const pool = new CognitoUserPool({ UserPoolId: USER_POOL_ID, ClientId: CLIENT_ID })

export function getCurrentUser() {
  return pool.getCurrentUser()
}

export function getIdToken() {
  return new Promise((resolve, reject) => {
    const user = pool.getCurrentUser()
    if (!user) return reject(new Error('No session'))
    user.getSession((err, session) => {
      if (err || !session?.isValid()) return reject(err || new Error('Invalid session'))
      resolve(session.getIdToken().getJwtToken())
    })
  })
}

export function login(email, password) {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: pool })
    const auth = new AuthenticationDetails({ Username: email, Password: password })
    user.authenticateUser(auth, {
      onSuccess: session => resolve(session.getIdToken().getJwtToken()),
      onFailure: reject,
      newPasswordRequired: () => reject(new Error('Se requiere cambio de contraseña')),
    })
  })
}

export function logout() {
  pool.getCurrentUser()?.signOut()
}
