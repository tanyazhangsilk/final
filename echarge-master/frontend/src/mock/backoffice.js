const userSeeds = [
  { name: '张伟', phone: '13800135678', vin_code: 'LGBH52E01NY100001', order_count: 86, total_spent: 4280.5, status: 'active', created_at: '2026-03-08 09:22' },
  { name: '李敏', phone: '13922345678', vin_code: 'LDC613P20N1000022', order_count: 53, total_spent: 2510.2, status: 'active', created_at: '2026-03-12 14:18' },
  { name: '陈静', phone: '13611112222', vin_code: 'LBV3A1E0XN1000044', order_count: 12, total_spent: 688, status: 'blacklisted', created_at: '2026-03-18 11:05' },
  { name: '王磊', phone: '13766889900', vin_code: 'LSVFA49J7N1000033', order_count: 39, total_spent: 1812.6, status: 'active', created_at: '2026-03-22 16:30' },
  { name: '周婷', phone: '13598761234', vin_code: 'LFV2A2150N1000088', order_count: 21, total_spent: 1280.4, status: 'active', created_at: '2026-03-25 08:45' },
  { name: '刘凯', phone: '13177778888', vin_code: 'LGBH41E03NY100077', order_count: 62, total_spent: 3366.8, status: 'active', created_at: '2026-03-29 19:12' },
]

export const mockAdminUsers = {
  summary: { total_users: 12486, active_users: 9210, blacklisted_users: 38 },
  rows: Array.from({ length: 96 }).map((_, index) => {
    const seed = userSeeds[index % userSeeds.length]
    return {
      id: index + 1,
      name: `${seed.name}${index > userSeeds.length - 1 ? ` ${index + 1}` : ''}`,
      phone: `1${String(3800000000 + index).padStart(10, '0')}`.slice(0, 11),
      vin_code: `${seed.vin_code.slice(0, 12)}${String(index + 1).padStart(5, '0')}`,
      order_count: seed.order_count + (index % 7) * 3,
      total_spent: Number((seed.total_spent + index * 16.8).toFixed(2)),
      status: index % 17 === 0 ? 'blacklisted' : seed.status,
      created_at: seed.created_at,
    }
  }),
}

export const mockBlacklistRows = [
  { id: 3, name: '陈静', phone: '13611112222', reason: '异常订单频发且存在支付争议', created_at: '2026-04-12 09:10' },
  { id: 4, name: '周峰', phone: '13598761234', reason: '多次触发风控规则', created_at: '2026-04-10 18:32' },
]

export const mockMarketingAudits = [
  { id: 1, name: '五一夜间充电补贴', operator_name: '深能星充', campaign_type: '折扣', discount_value: '8 折', audience: '夜间充电用户', audit_status: 'pending', remark: '待审核', submitted_at: '2026-04-08 10:30', budget: '¥80,000' },
  { id: 2, name: '物流车队返现活动', operator_name: '南粤智充', campaign_type: '返现', discount_value: '满 100 返 20', audience: '车队客户', audit_status: 'approved', remark: '已通过', submitted_at: '2026-04-06 14:20', budget: '¥120,000' },
  { id: 3, name: '周末快充服务券', operator_name: '湾区能联', campaign_type: '优惠券', discount_value: '20 元券', audience: '个人用户', audit_status: 'pending', remark: '待审核', submitted_at: '2026-04-11 09:50', budget: '¥36,000' },
  { id: 4, name: '新站上线拉新礼', operator_name: '深能星充', campaign_type: '满减', discount_value: '满 60 减 12', audience: '新注册用户', audit_status: 'rejected', remark: '预算口径需补充', submitted_at: '2026-04-05 16:10', budget: '¥50,000' },
]

export const mockPermissionModules = [
  { module: '工作台总览', view: true, edit: false, approve: false, export: true, scope: '平台概览' },
  { module: '运营商审核', view: true, edit: true, approve: true, export: true, scope: '入驻流程' },
  { module: '电站审核', view: true, edit: true, approve: true, export: true, scope: '站点准入' },
  { module: '全局订单', view: true, edit: true, approve: false, export: true, scope: '交易监管' },
  { module: '异常订单', view: true, edit: true, approve: true, export: true, scope: '风控处理' },
  { module: '平台清分', view: true, edit: true, approve: true, export: true, scope: '资金清分' },
  { module: '发票管理', view: true, edit: true, approve: false, export: true, scope: '票据处理' },
  { module: '用户管理', view: true, edit: true, approve: false, export: true, scope: '用户运营' },
  { module: '营销审核', view: true, edit: true, approve: true, export: false, scope: '活动审批' },
  { module: '系统参数', view: true, edit: true, approve: false, export: false, scope: '基础设置' },
]

export const mockSystemParams = {
  station_auto_publish: false,
  operator_auto_approve: false,
  station_public_requires_review: true,
  invoice_auto_approve_limit: 300,
  settlement_platform_rate: 10,
  settlement_cycle_days: 1,
  settlement_minimum_amount: 100,
  abnormal_order_sla_minutes: 30,
  user_refund_limit_per_day: 2,
  support_email: 'support@echarge.com',
  support_phone: '400-100-8899',
  notification_email_enabled: true,
  notification_sms_enabled: true,
  invoice_notice_enabled: true,
  abnormal_order_notify_roles: '平台运营, 财务审核, 客服值班',
}

export const mockOperatorStations = [
  {
    id: 101,
    operator_id: 1,
    operator_name: '深能星充',
    station_name: '南山科技园超充站',
    province: '广东省',
    city: '深圳市',
    district: '南山区',
    address: '高新南一道 008 号',
    full_address: '广东省 深圳市 南山区 高新南一道 008 号',
    longitude: 113.9461,
    latitude: 22.5404,
    contact_name: '刘洋',
    contact_phone: '13800001111',
    operation_hours: '00:00-24:00',
    parking_fee_desc: '前 30 分钟免费，之后 5 元/小时',
    station_remark: '覆盖园区办公与夜间补能场景',
    planned_charger_count: 16,
    total_power_kw: 1440,
    parking_slot_count: 48,
    service_radius_km: 5,
    site_owner: '园区物业',
    grid_capacity_remark: '现有配电容量 1800kVA，可支持二期扩容',
    construction_phase: '一期已投运',
    support_vehicle_types: ['乘用车', '网约车', '园区通勤车'],
    facility_tags: ['24小时', '休息区', '洗手间', '便利店'],
    safety_contact_name: '刘洋',
    safety_contact_phone: '13800001111',
    price_template_id: 1001,
    price_template_name: '城市快充工作日模板',
    charger_count: 14,
    visibility: 'public',
    visibility_text: '公开站点',
    status: 0,
    status_text: '已审核通过',
    audit_remark: '可正常运营',
    qualification_remark: '消防与配电资料齐全',
    created_at: '2026-04-01 10:20:00',
    updated_at: '2026-04-14 15:10:00',
  },
  {
    id: 102,
    operator_id: 1,
    operator_name: '深能星充',
    station_name: '福田会展中心充电站',
    province: '广东省',
    city: '深圳市',
    district: '福田区',
    address: '福华三路 118 号',
    full_address: '广东省 深圳市 福田区 福华三路 118 号',
    longitude: 114.0596,
    latitude: 22.5311,
    contact_name: '周宁',
    contact_phone: '13800002222',
    operation_hours: '07:00-23:00',
    parking_fee_desc: '商场停车标准',
    station_remark: '白天商务出行需求高',
    planned_charger_count: 10,
    total_power_kw: 720,
    parking_slot_count: 36,
    service_radius_km: 3,
    site_owner: '会展中心运营方',
    grid_capacity_remark: '待补充临时扩容方案与接入点说明',
    construction_phase: '待审核后开工',
    support_vehicle_types: ['乘用车', '商务车'],
    facility_tags: ['商场停车', '会议接驳', '夜间开放'],
    safety_contact_name: '周宁',
    safety_contact_phone: '13800002222',
    price_template_id: 1002,
    price_template_name: '商圈平峰模板',
    charger_count: 8,
    visibility: 'private',
    visibility_text: '未公开',
    status: 3,
    status_text: '待审核',
    audit_remark: '等待平台审核',
    qualification_remark: '需补充现场照片',
    created_at: '2026-04-10 09:10:00',
    updated_at: '2026-04-15 11:30:00',
  },
  {
    id: 103,
    operator_id: 1,
    operator_name: '深能星充',
    station_name: '宝安物流园补能站',
    province: '广东省',
    city: '深圳市',
    district: '宝安区',
    address: '航城大道 66 号',
    full_address: '广东省 深圳市 宝安区 航城大道 66 号',
    longitude: 113.8743,
    latitude: 22.6397,
    contact_name: '何帆',
    contact_phone: '13800003333',
    operation_hours: '00:00-24:00',
    parking_fee_desc: '园区免停车费',
    station_remark: '服务物流车队夜间集中补能',
    planned_charger_count: 20,
    total_power_kw: 1680,
    parking_slot_count: 72,
    service_radius_km: 8,
    site_owner: '物流园管委会',
    grid_capacity_remark: '待补充配电容量批复与消防联动说明',
    construction_phase: '一期建设中',
    support_vehicle_types: ['物流车', '轻卡', '冷链车'],
    facility_tags: ['车队专用', '夜间补能', '调度室'],
    safety_contact_name: '何峰',
    safety_contact_phone: '13800003333',
    price_template_id: null,
    price_template_name: '',
    charger_count: 12,
    visibility: 'private',
    visibility_text: '未公开',
    status: 4,
    status_text: '已驳回',
    audit_remark: '现场配电证明需补充',
    qualification_remark: '待补配电容量证明',
    created_at: '2026-03-28 18:40:00',
    updated_at: '2026-04-09 13:20:00',
  },
]

export const mockPricingTemplates = [
  {
    id: 1001,
    name: '城市快充工作日模板',
    peak_price: 1.88,
    flat_price: 1.26,
    valley_price: 0.72,
    service_price: 0.68,
    scope: 'station',
    status: 'active',
    updated_at: '2026-04-14 11:20:00',
    stations: 4,
    description: '适用于商务区白天高峰快充场景',
    periods: [
      { id: 1, type: 'peak', type_text: '高峰', time_range: '08:00-11:00, 17:00-21:00', ele_fee: 1.20, service_fee: 0.68 },
      { id: 2, type: 'flat', type_text: '平段', time_range: '11:00-17:00', ele_fee: 0.82, service_fee: 0.44 },
      { id: 3, type: 'valley', type_text: '低谷', time_range: '00:00-08:00, 21:00-24:00', ele_fee: 0.42, service_fee: 0.30 },
    ],
  },
  {
    id: 1002,
    name: '商圈平峰模板',
    peak_price: 1.68,
    flat_price: 1.18,
    valley_price: 0.66,
    service_price: 0.58,
    scope: 'station',
    status: 'active',
    updated_at: '2026-04-13 09:50:00',
    stations: 2,
    description: '适用于商圈短停补能场景',
    periods: [
      { id: 1, type: 'peak', type_text: '高峰', time_range: '10:00-13:00, 18:00-22:00', ele_fee: 1.10, service_fee: 0.58 },
      { id: 2, type: 'flat', type_text: '平段', time_range: '13:00-18:00', ele_fee: 0.78, service_fee: 0.40 },
      { id: 3, type: 'valley', type_text: '低谷', time_range: '00:00-10:00, 22:00-24:00', ele_fee: 0.38, service_fee: 0.28 },
    ],
  },
  {
    id: 1003,
    name: '物流夜间专用模板',
    peak_price: 1.42,
    flat_price: 1.02,
    valley_price: 0.55,
    service_price: 0.46,
    scope: 'station',
    status: 'draft',
    updated_at: '2026-04-12 19:10:00',
    stations: 0,
    description: '适用于夜间集中充电与车队长停场景',
    periods: [
      { id: 1, type: 'peak', type_text: '高峰', time_range: '07:00-09:00', ele_fee: 0.98, service_fee: 0.44 },
      { id: 2, type: 'flat', type_text: '平段', time_range: '09:00-18:00', ele_fee: 0.62, service_fee: 0.40 },
      { id: 3, type: 'valley', type_text: '低谷', time_range: '18:00-07:00', ele_fee: 0.25, service_fee: 0.30 },
    ],
  },
]

export const mockSettlementRows = [
  { id: 9001, settle_date: '2026-04-15', operator_id: 1, operator_name: '深能星充', order_count: 186, total_amount: 26890.34, platform_fee: 2689.03, settle_amount: 24201.31, platform_rate: 10, status: 1, status_text: '已打款', can_payout: true, hold_reason: '', created_at: '2026-04-16 09:10:00', updated_at: '2026-04-16 10:10:00' },
  { id: 9002, settle_date: '2026-04-14', operator_id: 1, operator_name: '深能星充', order_count: 174, total_amount: 25120.72, platform_fee: 2512.07, settle_amount: 22608.65, platform_rate: 10, status: 0, status_text: '待打款', can_payout: true, hold_reason: '', created_at: '2026-04-15 09:10:00', updated_at: '2026-04-15 10:10:00' },
  { id: 9003, settle_date: '2026-04-13', operator_id: 1, operator_name: '深能星充', order_count: 160, total_amount: 21988.4, platform_fee: 2198.84, settle_amount: 19789.56, platform_rate: 10, status: 2, status_text: '挂起待补资料', can_payout: false, hold_reason: '默认收款卡待审核', created_at: '2026-04-14 09:10:00', updated_at: '2026-04-14 10:10:00' },
]

export const mockCardInfo = {
  operator_id: 1,
  operator_name: '深能星充',
  operator_verified: true,
  audit_status: 'approved',
  audit_status_text: '已通过',
  cards: [
    {
      id: 1,
      account_name: '深圳星充运营服务有限公司',
      bank_name: '招商银行深圳科技园支行',
      bank_account_masked: '6225 **** **** 1888',
      bind_status: 1,
      bind_status_text: '审核通过',
      is_default: true,
      created_at: '2026-04-09 14:20:00',
      updated_at: '2026-04-10 09:00:00',
    },
  ],
  default_card: {
    id: 1,
    account_name: '深圳星充运营服务有限公司',
    bank_name: '招商银行深圳科技园支行',
    bank_account_masked: '6225 **** **** 1888',
    bind_status: 1,
    bind_status_text: '审核通过',
    is_default: true,
    created_at: '2026-04-09 14:20:00',
    updated_at: '2026-04-10 09:00:00',
  },
  settlement_eligible: true,
  settlement_tip: '绑卡审核通过，已具备 T+1 清分资格',
  settlement_notice: '绑卡审核通过后才可启动 T+1 清分；如遇法定节假日，打款按清算规则顺延至下一工作日。',
}

export const mockInvoiceRows = [
  { id: 1, invoice_no: 'INV202604150001', user_phone: '13800135678', operator_name: '深能星充', invoice_title: '深圳市南山科技有限公司', amount: 328.5, status: 0, status_text: '待开票', email: 'finance@nanshan-tech.com', created_at: '2026-04-15 10:10:00', remark: '' },
  { id: 2, invoice_no: 'INV202604140032', user_phone: '13922345678', operator_name: '深能星充', invoice_title: '个人', amount: 96.4, status: 1, status_text: '已开票', email: 'user02@example.com', created_at: '2026-04-14 15:30:00', file_url: 'https://echarge-system.com/invoices/INV202604140032.pdf', remark: '已发送邮箱通知' },
  { id: 3, invoice_no: 'INV202604130018', user_phone: '13611112222', operator_name: '深能星充', invoice_title: '深圳市物流发展有限公司', amount: 1288, status: 2, status_text: '已驳回', email: 'ap@logistics.com', created_at: '2026-04-13 09:45:00', remark: '抬头与税号不一致' },
]

export const mockCustomerOverview = {
  summary: { fleet_count: 18, whitelist_count: 6, member_count: 426 },
  members: [
    { id: 1, name: '深运物流 A 车队', phone: '0755-88886666', fleet_name: '深运物流', is_whitelist: true, status: '稳定运营' },
    { id: 2, name: '城配冷链 B 车队', phone: '0755-88889999', fleet_name: '城配冷链', is_whitelist: false, status: '待扩容' },
  ],
}

export const mockFleets = [
  { id: 1, name: '深运物流', member_count: 86, is_whitelist: true, created_at: '2026-03-15 10:20' },
  { id: 2, name: '城配冷链', member_count: 42, is_whitelist: false, created_at: '2026-03-18 14:05' },
]

export const mockTags = [
  { id: 1, name: '高频充电', color: '#0f766e', description: '近 30 天充电次数高于 20 次', user_count: 218 },
  { id: 2, name: '夜间活跃', color: '#2563eb', description: '22:00 后充电占比超过 60%', user_count: 134 },
]

export const mockDiscounts = [
  { id: 1, name: '夜间低谷折扣', campaign_type: '折扣', discount_value: '8.5 折', threshold: '满 40 可用', audience: '个人用户', redeem_count: 312, conversion_rate: '23.6%', status: '进行中' },
  { id: 2, name: '车队满减计划', campaign_type: '满减', discount_value: '满 100 减 15', threshold: '车队客户', audience: '车队客户', redeem_count: 88, conversion_rate: '18.2%', status: '待审核' },
]

export const mockCoupons = [
  { id: 1, name: '新客首充券', discount_value: '10 元', inventory: 5000, dispatched: 3200, used: 1468, status: '投放中' },
  { id: 2, name: '月度回流券', discount_value: '15 元', inventory: 2400, dispatched: 1200, used: 486, status: '待投放' },
]

export const mockOperatorProfile = {
  name: '深能星充运营服务有限公司',
  org_type: '充电站运营商',
  contact_email: 'ops@echarge.com',
  contact_phone: '0755-88990011',
  bank_account: '招商银行深圳科技园支行 / 6225 **** **** 1888',
  verified: true,
  station_count: 12,
  fleet_count: 6,
}

export const mockOperatorSettingContacts = [
  {
    id: 1,
    module: '运营值守',
    owner: '调度中心',
    contact_phone: '0755-88990011',
    contact_email: 'dispatch@echarge.com',
    status: 'active',
    updated_at: '2026-04-16 09:30',
  },
  {
    id: 2,
    module: '客户服务',
    owner: '客服团队',
    contact_phone: '400-800-1122',
    contact_email: 'service@echarge.com',
    status: 'active',
    updated_at: '2026-04-15 14:10',
  },
  {
    id: 3,
    module: '财务对账',
    owner: '财务结算组',
    contact_phone: '0755-88990022',
    contact_email: 'finance@echarge.com',
    status: 'active',
    updated_at: '2026-04-14 18:25',
  },
  {
    id: 4,
    module: '市场合作',
    owner: '运营拓展组',
    contact_phone: '0755-88990033',
    contact_email: 'growth@echarge.com',
    status: 'standby',
    updated_at: '2026-04-13 11:45',
  },
]
