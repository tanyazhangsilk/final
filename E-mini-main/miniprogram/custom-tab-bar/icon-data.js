// 图标 SVG 转 data URL（灰色 #999 和蓝色 #06b6d4）
const gray = '#999'
const blue = '#06b6d4'

function svgToDataUrl(svg) {
  return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg)
}

const icons = {
  home: {
    default: svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${gray}"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg>`),
    active: svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${blue}"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg>`),
  },
  station: {
    default: svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${gray}"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>`),
    active: svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${blue}"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>`),
  },
  charge: {
    default: svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${gray}"><path d="M7 2v11h3v9l7-12h-3V2z"/></svg>`),
    active: svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${blue}"><path d="M7 2v11h3v9l7-12h-3V2z"/></svg>`),
  },
  wallet: {
    default: svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${gray}"><path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8z"/></svg>`),
    active: svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${blue}"><path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8z"/></svg>`),
  },
  profile: {
    default: svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${gray}"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>`),
    active: svgToDataUrl(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${blue}"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>`),
  },
}

module.exports = icons
