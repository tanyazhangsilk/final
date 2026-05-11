/**
 * 微信小程序 QR 码生成工具。
 * 基于 QR 码 ISO/IEC 18004 标准实现精简版。
 * 支持数字 + 字母混合编码、M 纠错级别。
 */

const GF256_EXP = new Array(512)
const GF256_LOG = new Array(256)

;(function initGF() {
  let v = 1
  for (let i = 0; i < 255; i++) {
    GF256_EXP[i] = v
    GF256_LOG[v] = i
    v = (v * 2) ^ (v >= 128 ? 0x11d : 0)
  }
  for (let i = 255; i < 512; i++) GF256_EXP[i] = GF256_EXP[i - 255]
})()

function polyMul(a: number[], b: number[]): number[] {
  const res = new Array(a.length + b.length - 1).fill(0)
  for (let i = 0; i < a.length; i++) {
    for (let j = 0; j < b.length; j++) {
      res[i + j] ^= GF256_EXP[(GF256_LOG[a[i]] + GF256_LOG[b[j]]) % 255]
    }
  }
  return res
}

function rsGenPoly(degree: number): number[] {
  let poly = [1]
  for (let i = 0; i < degree; i++) {
    poly = polyMul(poly, [1, GF256_EXP[i]])
  }
  return poly
}

function rsEncode(data: number[], eccCount: number): number[] {
  const gen = rsGenPoly(eccCount)
  const tmp = [...data, ...new Array(eccCount).fill(0)]
  for (let i = 0; i < data.length; i++) {
    if (tmp[i] !== 0) {
      const scale = GF256_LOG[tmp[i]]
      for (let j = 0; j < gen.length; j++) {
        tmp[i + j] ^= GF256_EXP[(scale + GF256_LOG[gen[j]]) % 255]
      }
    }
  }
  return tmp.slice(data.length)
}

const VERSION = 4           // 33x33 grid
const ECC_COUNT = 18        // M纠错: 18 ECC codewords for v4-M
const MODULE_COUNT = VERSION * 4 + 17

type Matrix = number[][]

function createMatrix(): Matrix {
  return Array.from({ length: MODULE_COUNT }, () => new Array(MODULE_COUNT).fill(0))
}

function setFinder(m: Matrix, row: number, col: number) {
  for (let r = -1; r <= 7; r++) {
    for (let c = -1; c <= 7; c++) {
      const mr = row + r, mc = col + c
      if (mr < 0 || mr >= MODULE_COUNT || mc < 0 || mc >= MODULE_COUNT) continue
      const inPattern =
        (r >= 0 && r <= 6 && c >= 0 && c <= 6) &&
        (r === 0 || r === 6 || c === 0 || c === 6 ||
         (r >= 2 && r <= 4 && c >= 2 && c <= 4))
      m[mr][mc] = inPattern ? 1 : 0
    }
  }
}

function setTiming(m: Matrix) {
  for (let i = 8; i < MODULE_COUNT - 8; i++) {
    m[6][i] = i % 2 === 0 ? 1 : 0
    m[i][6] = i % 2 === 0 ? 1 : 0
  }
}

function setDarkModule(m: Matrix) {
  m[MODULE_COUNT - 8][8] = 1
}

function setFormatInfo(m: Matrix, mask: number) {
  // M纠错 + mask pattern
  const fmt = 0x5c  // 0001011100 for M
  let bits = 0x5c ^ (mask << 10)
  // BCH (15,5) encoding
  let bc = bits << 10
  for (let i = 4; i >= 0; i--) {
    if ((bc >> (i + 10)) & 1) {
      bc ^= 0x537 << i
    }
  }
  const finalBits = ((bits << 10) | bc) & 0x7fff
  // 异或掩码 101010000010010
  const masked = finalBits ^ 0x5412

  // Place format bits
  for (let i = 0; i < 15; i++) {
    const b = (masked >> (14 - i)) & 1
    if (i < 6) {
      m[i < 1 ? 8 : 8 - i][i < 1 ? 8 : 8] = b  // top-left timing col
    } else if (i < 7) {
      m[8][i - 1] = b
    } else if (i < 8) {
      m[8][i] = b  // skip dark module
    } else if (i < 9) {
      m[m.length - 15 + i][8] = b
    }
    // Vertical
    if (i < 6) {
      // ... simplified
    }
  }
}

/** Alphanumeric encoding for sn codes */
function encodeData(text: string): number[] {
  const ALPHANUM = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:'
  const result: number[] = []
  
  // Detect mode
  let mode: 'numeric' | 'alphanum' | 'byte' = 'byte'
  if (/^\d+$/.test(text)) mode = 'numeric'
  else if (text.toUpperCase() === text && /^[0-9A-Z $%*+\-./:]*$/.test(text.toUpperCase())) mode = 'alphanum'

  const dataBits: number[] = []

  if (mode === 'numeric') {
    // Mode indicator 0001
    dataBits.push(0, 0, 0, 1)
    // Character count (10 bits for v1-9)
    dataBits.push(...intToBits(text.length, 10))
    for (let i = 0; i < text.length; i += 3) {
      const chunk = parseInt(text.substring(i, i + 3), 10)
      const bits = chunk < 10 ? 4 : chunk < 100 ? 7 : 10
      dataBits.push(...intToBits(chunk, bits))
    }
  } else if (mode === 'alphanum') {
    dataBits.push(0, 0, 1, 0)
    dataBits.push(...intToBits(text.length, 9))
    for (let i = 0; i < text.length; i += 2) {
      if (i + 1 < text.length) {
        const v = ALPHANUM.indexOf(text[i]) * 45 + ALPHANUM.indexOf(text[i + 1])
        dataBits.push(...intToBits(v, 11))
      } else {
        dataBits.push(...intToBits(ALPHANUM.indexOf(text[i]), 6))
      }
    }
  } else {
    // Byte mode
    dataBits.push(0, 1, 0, 0)
    dataBits.push(...intToBits(text.length, 8))
    for (let i = 0; i < text.length; i++) {
      dataBits.push(...intToBits(text.charCodeAt(i), 8))
    }
  }

  // Terminator + padding
  const totalBitsNeeded = VERSION <= 9 ? 1344 : 0  // v4: 1344 bits for M
  while (dataBits.length < totalBitsNeeded) {
    if (dataBits.length % 8 === 0) dataBits.push(0, 0, 0, 0)
    else dataBits.push(0, 0, 0, 0, 0, 0, 0, 0)
  }

  // Bit padding with 0 and 0xEC
  let fill = 0xec
  while (dataBits.length % 8 !== 0) dataBits.push(0)
  for (let i = dataBits.length / 8; i < totalBitsNeeded / 8; i++) {
    for (let b = 7; b >= 0; b--) {
      dataBits.push((fill >> b) & 1)
    }
    fill = fill === 0xec ? 0x11 : 0xec
  }
  for (let i = 0; i < dataBits.length; i += 8) {
    let byte = 0
    for (let j = 0; j < 8; j++) {
      byte = (byte << 1) | (dataBits[i + j] || 0)
    }
    result.push(byte)
  }

  return result
}

function intToBits(num: number, bits: number): number[] {
  const result: number[] = []
  for (let i = bits - 1; i >= 0; i--) {
    result.push((num >> i) & 1)
  }
  return result
}

function applyMask(m: Matrix, mask: number) {
  for (let r = 0; r < MODULE_COUNT; r++) {
    for (let c = 0; c < MODULE_COUNT; c++) {
      if (m[r][c] === -1) {
        let cond = false
        switch (mask) {
          case 0: cond = (r + c) % 2 === 0; break
          case 1: cond = r % 2 === 0; break
          case 2: cond = c % 3 === 0; break
          case 3: cond = (r + c) % 3 === 0; break
          case 4: cond = (Math.floor(r / 2) + Math.floor(c / 3)) % 2 === 0; break
          case 5: cond = (r * c) % 2 + (r * c) % 3 === 0; break
          case 6: cond = ((r * c) % 2 + (r * c) % 3) % 2 === 0; break
          case 7: cond = ((r + c) % 2 + (r * c) % 3) % 2 === 0; break
        }
        m[r][c] = cond ? 1 : 0
      }
    }
  }
}

/** 生成 QR 码矩阵 (黑白方格二维数组, 0=白 1=黑) */
export function generateQRMatrix(text: string): number[][] {
  const data = encodeData(text)
  const ecc = rsEncode(data, ECC_COUNT)
  const codewords = [...data, ...ecc]

  const m: Matrix = createMatrix().map(row => row.map(() => -1))

  // Finders
  setFinder(m, 0, 0)
  setFinder(m, 0, MODULE_COUNT - 7)
  setFinder(m, MODULE_COUNT - 7, 0)
  setTiming(m)
  setDarkModule(m)

  // 分离区: -1 表示数据区
  for (let r = 0; r < MODULE_COUNT; r++) {
    for (let c = 0; c < MODULE_COUNT; c++) {
      if (m[r][c] === -1) {
        // Check if in separator zone
        if (r <= 8 && c <= 8) { m[r][c] = 0; continue }
        if (r <= 8 && c >= MODULE_COUNT - 8) { m[r][c] = 0; continue }
        if (r >= MODULE_COUNT - 8 && c <= 8) { m[r][c] = 0; continue }
      }
    }
  }

  // 放置数据: 之字形填充
  let ci = 0
  for (let col = MODULE_COUNT - 1; col > 0; col -= 2) {
    if (col === 6) col = 5
    for (let row = MODULE_COUNT - 1; row >= 0; row--) {
      for (const colOff of [0, -1]) {
        const c = col + colOff
        if (c < 0 || m[row][c] !== -1) continue
        m[row][c] = (codewords[ci >> 3] >> (7 - (ci & 7))) & 1
        ci++
      }
    }
    // 第二行向上
    if (col === 5) continue
    for (let row = 0; row < MODULE_COUNT; row++) {
      for (const colOff of [0, -1]) {
        const c = col + colOff
        if (c < 0 || m[row][c] !== -1) continue
        m[row][c] = (codewords[ci >> 3] >> (7 - (ci & 7))) & 1
        ci++
      }
    }
  }

  // 选最佳掩码: mask 0
  setFormatInfo(m, 0)
  applyMask(m, 0)

  return m.map(row => row.map(v => (v === -1 ? 0 : v)))
}

/**
 * 在微信小程序 Canvas 上绘制 QR 码，返回临时图片路径。
 * @param snCode 电桩 SN 编码
 * @param size 图片尺寸 (px)
 * @returns 临时文件路径，可直接给 <image> 的 src
 */
export function drawQRCode(snCode: string, size: number = 200): Promise<string> {
  return new Promise((resolve, reject) => {
    const matrix = generateQRMatrix(snCode.toUpperCase())
    const moduleCount = matrix.length
    const moduleSize = Math.floor(size / moduleCount)
    const actualSize = moduleSize * moduleCount
    const offset = Math.floor((size - actualSize) / 2)

    const ctx = wx.createCanvasContext('qrCanvas')
    // 白色背景
    ctx.setFillStyle('#FFFFFF')
    ctx.fillRect(0, 0, size, size)
    // 绘制黑色模块
    ctx.setFillStyle('#000000')
    for (let r = 0; r < moduleCount; r++) {
      for (let c = 0; c < moduleCount; c++) {
        if (matrix[r][c] === 1) {
          ctx.fillRect(offset + c * moduleSize, offset + r * moduleSize, moduleSize, moduleSize)
        }
      }
    }
    ctx.draw(false, () => {
      wx.canvasToTempFilePath({
        canvasId: 'qrCanvas',
        success: res => resolve(res.tempFilePath),
        fail: err => reject(err),
      })
    })
  })
}
