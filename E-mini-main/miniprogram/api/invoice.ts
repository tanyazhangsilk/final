import { get } from '../utils/request'

export function getInvoiceList() {
  return get('/invoices')
}
