# E-mini 小程序联调说明

## 打开方式

请使用微信开发者工具直接打开 `E-mini/miniprogram` 目录，不要打开仓库根目录。

## 后端地址

开发环境默认 `baseUrl = http://127.0.0.1:8000/api/v1`。

如果微信开发者工具里访问 `127.0.0.1` 不通，请把 `miniprogram/config/env.ts` 里的地址替换为本机局域网 IP，例如 `http://192.168.x.x:8000/api/v1`。

## 开发者工具设置

在微信开发者工具的“详情”里勾选“不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书”。

## 演示链路

完整演示建议按下面顺序走：

首页 → 附近电站 → 电站详情 → 扫码/输入桩号 → 开始充电 → 充电监控 → 结束充电 → 订单详情 → 钱包流水

## 接口与兜底说明

- 小程序真实接口封装在 `miniprogram/services/request.ts` 和 `miniprogram/services/api.ts`
- 页面会优先请求后端 API
- 如果后端不可用，会自动回退到 `miniprogram/services/mock.ts`
- 这样即使本地后端未启动，演示也不会因为接口失败直接白屏
