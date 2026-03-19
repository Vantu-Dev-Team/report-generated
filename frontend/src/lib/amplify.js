import { Amplify } from 'aws-amplify'

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID,
      userPoolClientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
      loginWith: {
        username: true,
        email: true,
        oauth: {
          domain: import.meta.env.VITE_COGNITO_DOMAIN,
          scopes: ['openid', 'email', 'profile'],
          redirectSignIn: [
            'http://localhost:5173/',
            'https://reports.sentoapp.net/',
            'https://master.d1l9zrx2p5onp7.amplifyapp.com/',
          ],
          redirectSignOut: [
            'http://localhost:5173/login',
            'https://reports.sentoapp.net/login',
            'https://master.d1l9zrx2p5onp7.amplifyapp.com/login',
          ],
          responseType: 'code',
          providers: [{ custom: 'Google' }],
        },
      },
    },
  },
})
