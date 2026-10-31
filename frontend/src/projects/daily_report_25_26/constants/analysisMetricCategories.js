// 参照月报“指标大类—业务子类”组织日报指标；按编码归类，名称变更不会改变归属。
const categories = {
  primary: [
    ['production', '主要产销指标', [
      'amount_power_generation', 'amount_power_sales', 'amount_heat_supply', 'amount_steam_supply',
      'amount_network_interface_heat_supply', 'amount_hot_water_sales', 'amount_steam_sales',
    ]],
    ['consumption', '主要消耗指标', [
      'consumption_amount_raw_coal', 'consumption_std_coal', 'consumption_amount_raw_coal_zhangtun',
      'consumption_std_coal_zhangtun', 'consumption_natural_gas', 'consumption_water',
      'consumption_plant_water', 'consumption_network_water', 'consumption_network_fill_water',
      'consumption_station_fill_water', 'consumption_purchased_power', 'consumption_plant_purchased_power',
      'consumption_station_purchased_power', 'consumption_outer_purchased_heat',
    ]],
    ['materials', '辅材消耗指标', [
      'consumption_acid', 'consumption_alkali', 'consumption_oil', 'consumption_ammonia_water',
      'consumption_limestone_powder', 'consumption_limestone', 'consumption_magnesium_oxide', 'consumption_denitration_agent',
    ]],
    ['efficiency', '能效与供暖单耗', [
      'rate_overall_efficiency', 'rate_std_coal_per_heat', 'rate_heat_per_10k_m2',
      'rate_power_per_10k_m2', 'rate_water_per_10k_m2',
    ]],
    ['loss', '站耗与热网损耗', ['consumption_station_heat', 'amount_heat_lose', 'eco_heat_lose']],
    ['income', '经营收入指标', [
      'eco_direct_income', 'eco_power_supply_income', 'eco_inner_heat_supply_income',
      'eco_heating_supply_income', 'eco_hot_water_supply_income', 'eco_steam_supply_income',
    ]],
    ['cost', '成本与利润指标', [
      'eco_coal_cost', 'eco_natural_gas_cost', 'eco_purchased_power_cost', 'eco_purchased_water_cost',
      'eco_measurable_auxiliary_materials', 'eco_inner_purchased_heat_cost', 'eco_outer_heat_cost',
      'eco_marginal_profit', 'eco_comparable_marginal_profit',
    ]],
    ['equipment', '设备运行与生产事件', [
      'amount_boiler_steam_running', 'amount_boiler_water_running', 'amount_boiler_gas_running',
      'amount_turbine_running', 'amount_boiler_room_running', 'amount_electric_boiler_running',
      'amount_heat_pump_running', 'equipment_on_off_status', 'additional_information',
    ]],
    ['service', '供热服务与投诉', [
      'amount_daily_service_complaints', 'amount_daily_net_complaints', 'amount_daily_provincial_net_complaints',
      'amount_daily_city_net_complaints', 'amount_daily_net_complaints_per_10k_m2',
      'sum_month_total_net_complaints', 'sum_season_total_net_complaints',
    ]],
    ['weather', '日报气温记录', ['amount_temp_highest', 'amount_temp_lowest']],
  ],
  constant: [
    ['energy_prices', '能源与水热单价', [
      'price_power_sales', 'price_inner_heat_sales', 'price_std_coal', 'price_std_coal_comparable',
      'price_purchased_power', 'price_purchased_water', 'price_natural_gas', 'price_hot_water_sales',
      'price_steam_sales', 'price_inner_purchased_heat', 'price_outer_purchased_heat',
    ]],
    ['material_prices', '辅材单价', [
      'price_acid', 'price_alkali', 'price_oil', 'price_n_ammonia_water', 'price_limestone_powder',
      'price_limestone', 'price_magnesium_oxide', 'price_denitration_agent',
    ]],
    ['area', '供暖面积', ['amount_whole_heating_area', 'amount_heating_fee_area']],
    ['income_ratio', '采暖期收入与分摊', ['eco_season_heating_income', 'rate_sharing_ratio']],
  ],
  adjustment: [
    ['coal_adjustment', '张屯煤耗汇总', ['sum_consumption_amount_raw_coal_zhangtun', 'sum_consumption_std_coal_zhangtun']],
    ['rate_adjustment', '供暖单耗调整', ['rate_power_per_10k_m2_YanJiuYuan']],
  ],
  temperature: [['temperature', '气温分析指标', ['aver_temp', 'max_temp', 'min_temp']]],
}

export function classifyAnalysisMetrics(groups) {
  return groups.map(group => {
    const definitions = categories[group.key] || []
    const assigned = new Set()
    const subgroups = definitions.map(([key, label, keys]) => {
      const allowed = new Set(keys)
      const options = group.options.filter(option => allowed.has(option.value) && !assigned.has(option.value))
      options.forEach(option => assigned.add(option.value))
      return { key, label, options }
    }).filter(subgroup => subgroup.options.length)
    // 新增指标保持可选，不因分类表尚未更新而被隐藏。
    const remaining = group.options.filter(option => !assigned.has(option.value))
    if (remaining.length) subgroups.push({ key: 'other', label: definitions.length ? '其他指标' : group.label, options: remaining })
    return { ...group, subgroups }
  })
}

export function isMetricCategorySelected(selected, options) {
  return options.length > 0 && options.every(option => selected.has(option.value))
}

export function toggleMetricCategory(selected, options) {
  const next = new Set(selected)
  const remove = isMetricCategorySelected(selected, options)
  for (const option of options) {
    if (remove) next.delete(option.value)
    else next.add(option.value)
  }
  return next
}
