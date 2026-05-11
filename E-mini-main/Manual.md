# E-Charge 充电桩小程序 - 使用手册

## 项目结构

```
miniprogram/
├── app.json          # 页面路由、tabBar 配置
├── app.ts            # 全局逻辑
├── utils/
│   ├── data.ts       # 充电站 mock 数据
│   └── storage.ts    # 用户、余额本地存储
├── pages/
│   ├── login/        # 登录
│   ├── register/     # 注册
│   ├── home/         # 首页
│   ├── stations/     # 附近电站
│   ├── scan/         # 扫码充电
│   ├── wallet/       # 我的钱包
│   ├── profile/      # 我的
│   ├── charging-records/  # 充电记录
│   └── orders/       # 订单管理
└── assets/icons/     # tabBar 图标（占位）
```

## 使用说明

1. **首次使用**：在注册页完成注册，注册后自动登录并进入首页。
2. **登录**：使用已注册的邮箱和密码登录。
3. **充值**：在「我的钱包」点击「充值」，输入金额即可（当前为本地模拟）。
