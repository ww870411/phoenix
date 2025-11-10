CREATE OR REPLACE VIEW calc_temperature_data AS
SELECT
    DATE_TRUNC('day', date_time AT TIME ZONE 'Asia/Shanghai')::date AS date,
    MAX(value) AS max_temp,
    MIN(value) AS min_temp,
    AVG(value) AS aver_temp
FROM temperature_data
GROUP BY DATE_TRUNC('day', date_time AT TIME ZONE 'Asia/Shanghai')::date
ORDER BY date;
