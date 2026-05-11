import { post } from '../utils/request'

export interface LoginPayload {
  code?: string,
  phone?: string,
  password?: string
}

export function login(data: LoginPayload) {
  return post('/auth/login', data)
}
