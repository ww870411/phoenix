-- 动态计划月度分解气温敏感度建议 k 参数表
-- 源数据：configs/10.27（4） 完整指标_最新情况导入用.xlsx

CREATE TABLE IF NOT EXISTS public.dynamic_month_plan_k (
    id SERIAL PRIMARY KEY,
    model_no INT,
    company TEXT NOT NULL,
    company_cn TEXT,
    month INT NOT NULL,
    item TEXT NOT NULL,
    item_cn TEXT,
    unit TEXT,
    k_value NUMERIC(24, 16) NOT NULL,
    m_value NUMERIC(16, 6) NOT NULL DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 联合唯一索引：保障同单位、同月份、同指标幂等更新
CREATE UNIQUE INDEX IF NOT EXISTS idx_dynamic_month_plan_k_unique 
ON public.dynamic_month_plan_k (company, month, item);
