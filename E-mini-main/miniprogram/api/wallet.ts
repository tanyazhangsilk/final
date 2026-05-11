import { get } from '../utils/request'

export function getWalletSummary() {
  return get('/wallet')
}
