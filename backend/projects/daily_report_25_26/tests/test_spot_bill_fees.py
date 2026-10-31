"""账单电费汇总回归：本地真实数据库验证，全部变更由外层事务回滚。"""
from datetime import date
from decimal import Decimal
import unittest
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db.database_daily_report_25_26 import engine
from backend.projects.daily_report_25_26.api import spot_electricity as api


class BillFeeTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.addCleanup(self.connection.close)
        self.addCleanup(self.transaction.rollback)
        self.day = date(2098, 5, 20)
        self.factory = lambda: Session(bind=self.connection, join_transaction_mode='create_savepoint')
        self.assertEqual(self.connection.execute(text('SELECT count(*) FROM public.spot_electricity_15min_data WHERE trade_date=:day'),
                                                {'day': self.day}).scalar(), 0, '测试日期已有业务数据，停止测试')
        records = []
        for point in range(1, 97):
            row = {'trade_date': self.day, 'point_index': point, 'time_label': f'{point // 4:02d}:{point % 4 * 15:02d}',
                   'bill_real_time_price': -10 if point % 2 else 20, 'real_time_price': 999}
            for plant, units in (('beihai', 3), ('xianghai', 4)):
                for n in range(1, units + 1):
                    row[f'{plant}_unit{n}_sales'] = 0 if n == 2 else n * (3 if point % 2 else 1)
                    row[f'{plant}_unit{n}_contract_quantity'] = Decimal(n) / 2
                    row[f'{plant}_unit{n}_contract_price'] = -30 if n == 3 else n * 10
            records.append(row)
        columns = list(records[0])
        self.connection.execute(text(f'INSERT INTO public.spot_electricity_15min_data ({",".join(columns)}) '
                                     f'VALUES ({",".join(":" + c for c in columns)})'), records)

    def summary(self, end='2098-05-20'):
        with patch.object(api, 'SessionLocal', self.factory):
            return api.get_spot_electricity_summary('2098-05-20', end, session=None)['data']

    def test_per_period_products_bill_price_and_stopped_unit_contract(self):
        result = self.summary()
        # 48个负价点的电量为正价点三倍，不能用日总电量乘平均价格替代逐点乘积。
        self.assertEqual(result['sum_beihai_spot_fee'], -1920)
        self.assertEqual(result['sum_xianghai_spot_fee'], -3840)
        # 停机的2号机组仍有20元合约差价；不减实时价，不乘0.25，不舍弃负值。
        self.assertEqual(result['sum_beihai_contract_fee'], -1920)
        self.assertEqual(result['sum_xianghai_contract_fee'], 5760)

        self.assertEqual(result['sum_beihai_revenue_fee'], -3840)
        self.assertEqual(result['sum_xianghai_revenue_fee'], 1920)
        self.assertEqual(result['avg_beihai_spot_price'], -2.5)
        self.assertEqual(result['avg_xianghai_spot_price'], -2.5)
        # 参考实时价为999，账单加权均价为-2.5，不使用账单均价作为比较基准。
        self.assertAlmostEqual(result['beihai_spot_price_diff_rate'], (-2.5 - 999) / 999 * 100)

    def test_missing_contract_or_bill_price_does_not_report_partial_total(self):
        self.connection.execute(text("UPDATE public.spot_electricity_15min_data SET beihai_unit1_contract_price=NULL WHERE trade_date=:day AND point_index=1"), {'day': self.day})
        result = self.summary()
        self.assertIsNone(result['sum_beihai_contract_fee'])
        self.assertIsNone(result['sum_beihai_revenue_fee'])
        self.assertEqual(result['sum_xianghai_contract_fee'], 5760)
        self.assertEqual(result['sum_beihai_spot_fee'], -1920)
        self.connection.execute(text("UPDATE public.spot_electricity_15min_data SET bill_real_time_price=NULL WHERE trade_date=:day AND point_index=1"), {'day': self.day})
        result = self.summary()
        self.assertIsNone(result['sum_beihai_spot_fee'])
        self.assertIsNone(result['avg_beihai_spot_price'])
        self.assertIsNone(result['beihai_spot_price_diff_rate'])
        self.assertIsNone(result['sum_xianghai_spot_fee'])
        self.assertIsNone(result['sum_xianghai_revenue_fee'])
        self.assertEqual(result['sum_xianghai_contract_fee'], 5760)

    def test_missing_period_or_day_is_incomplete(self):
        self.assertIsNone(self.summary('2098-05-21')['sum_beihai_spot_fee'])
        self.connection.execute(text('DELETE FROM public.spot_electricity_15min_data WHERE trade_date=:day AND point_index=96'), {'day': self.day})
        result = self.summary()
        for key in ('sum_beihai_spot_fee', 'sum_xianghai_spot_fee', 'sum_beihai_contract_fee', 'sum_xianghai_contract_fee'):
            self.assertIsNone(result[key], key)

    def test_complete_zero_values_are_zero(self):
        assignments = [f'{plant}_unit{n}_{field}=0' for plant, units in (('beihai', 3), ('xianghai', 4))
                       for n in range(1, units + 1) for field in ('sales', 'contract_quantity')]
        self.connection.execute(text(f'UPDATE public.spot_electricity_15min_data SET {",".join(assignments)} WHERE trade_date=:day'), {'day': self.day})
        result = self.summary()
        for key in ('sum_beihai_spot_fee', 'sum_xianghai_spot_fee', 'sum_beihai_contract_fee', 'sum_xianghai_contract_fee'):
            self.assertEqual(result[key], 0, key)
        self.assertIsNone(result['avg_beihai_spot_price'])
        self.assertIsNone(result['avg_xianghai_spot_price'])

    def test_zero_reference_price_keeps_weighted_average_without_rate(self):
        self.connection.execute(text('UPDATE public.spot_electricity_15min_data SET real_time_price=0 WHERE trade_date=:day'), {'day': self.day})
        result = self.summary()
        self.assertEqual(result['avg_beihai_spot_price'], -2.5)
        self.assertIsNone(result['beihai_spot_price_diff_rate'])
        self.assertIsNone(result['xianghai_spot_price_diff_rate'])

    def test_revenue_adds_unrounded_fees(self):
        assignments = [f'{plant}_unit{n}_{field}=0' for plant, units in (('beihai', 3), ('xianghai', 4))
                       for n in range(1, units + 1) for field in ('sales', 'contract_quantity')]
        self.connection.execute(text(f'UPDATE public.spot_electricity_15min_data SET {",".join(assignments)} WHERE trade_date=:day'), {'day': self.day})
        self.connection.execute(text('UPDATE public.spot_electricity_15min_data SET beihai_unit1_sales=1, bill_real_time_price=0.4, '
                                     'beihai_unit1_contract_quantity=1, beihai_unit1_contract_price=0.4 '
                                     'WHERE trade_date=:day AND point_index=1'), {'day': self.day})
        result = self.summary()
        self.assertEqual(result['sum_beihai_spot_fee'], 0.4)
        self.assertEqual(result['sum_beihai_contract_fee'], 0.4)
        self.assertEqual(result['sum_beihai_revenue_fee'], 0.8)

    def test_sales_availability_uses_metered_fields_and_keeps_zero(self):
        self.assertTrue(self.summary()['has_plant_sales_data'])
        assignments = [f'{plant}_unit{n}_sales=NULL' for plant, units in (('beihai', 3), ('xianghai', 4))
                       for n in range(1, units + 1)]
        self.connection.execute(text(f'UPDATE public.spot_electricity_15min_data SET {",".join(assignments)} WHERE trade_date=:day'), {'day': self.day})
        self.assertFalse(self.summary()['has_plant_sales_data'])
        self.connection.execute(text('UPDATE public.spot_electricity_15min_data SET beihai_unit1_sales=0 WHERE trade_date=:day AND point_index=1'), {'day': self.day})
        # 合约数据不代表上网电量存在；真实零值代表存在，即使其他机组暂缺。
        self.assertTrue(self.summary()['has_plant_sales_data'])


if __name__ == '__main__':
    unittest.main()
