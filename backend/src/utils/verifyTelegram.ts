// utils.ts
export async function verifyTelegramHash(initData: string, botToken: string): Promise<boolean> {
  const params = new URLSearchParams(initData)
  const hash = params.get('hash')
  params.delete('hash')

  const dataCheckString = Array.from(params.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}=${v}`)
    .join('\n')

  // Create secret key: HMAC_SHA256("WebAppData", botToken)
  const encoder = new TextEncoder()
  const webAppDataKey = await crypto.subtle.importKey(
    'raw',
    encoder.encode('WebAppData'),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  )
  
  const secretKey = await crypto.subtle.sign('HMAC', webAppDataKey, encoder.encode(botToken))
  
  // Calculate hash: HMAC_SHA256(secret_key, data_check_string)
  const secretKeyForHash = await crypto.subtle.importKey(
    'raw',
    secretKey,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  )
  
  const calculatedHash = await crypto.subtle.sign('HMAC', secretKeyForHash, encoder.encode(dataCheckString))
  const calculatedHashHex = Array.from(new Uint8Array(calculatedHash))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')

  return hash === calculatedHashHex
}