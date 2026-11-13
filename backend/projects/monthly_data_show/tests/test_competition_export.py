# -*- coding: utf-8 -*-
"""
供暖期指标竞赛 3-Sheet Excel 导出服务单元测试。
"""

import io
import unittest

import openpyxl

from backend.projects.monthly_data_show.api.workspace import (
    ExportCompetitionExcelRequest,
    post_competition_export_excel,
)
from backend.projects.monthly_data_show.services.competition_export_service import (
    generate_competition_excel,
)


def _sample_complete_units():
    """构造完整的 7 家参评单位测试数据（含红榜、一般事故、黑榜否决情形）。"""
    return [
        {
            "code": "BeiHai",
            "name": "北海热电厂",
            "type": "热电厂",
            "baseAmount": 70000,
            "score": 100.38,
            "pendingCount": 0,
            "eligible": True,
            "disqualifyReason": "",
            "isBlackListed": False,
            "isRedListed": False,
            "hasMajorAccident": False,
            "hasGeneralAccident": False,
            "indicators": [
                {"name": "耗标煤总量", "weight": 30, "unit": "吨", "hasTarget": True, "targetValue": 52000, "actualValue": 51000, "score": 30.58, "calcType": "energy_saving", "sourceLabel": "月报表"},
                {"name": "厂内水耗量", "weight": 10, "unit": "吨", "hasTarget": True, "targetValue": 48000, "actualValue": 47000, "score": 10.21, "calcType": "consumption", "sourceLabel": "月报表"},
                {"name": "现货电价", "weight": 20, "unit": "元/MWh", "hasTarget": True, "targetValue": 234.63, "actualValue": 250.10, "score": 22.20, "calcType": "spot_price", "sourceLabel": "电力现货市场"},
                {"name": "全厂热效率", "weight": 20, "unit": "%", "hasTarget": True, "targetValue": 78.5, "actualValue": 78.0, "score": 18.73, "calcType": "efficiency", "sourceLabel": "月报表"},
                {"name": "非计划停炉停机", "weight": 10, "unit": "次", "hasTarget": False, "targetValue": 0, "actualValue": 0, "score": 10.0, "calcType": "shutdown", "sourceLabel": "手动填报"},
                None,
                {"name": "安全文明生产", "weight": 10, "unit": "分", "hasTarget": False, "targetValue": 10, "actualValue": 8.66, "score": 8.66, "calcType": "civic", "sourceLabel": "检查评定"},
            ],
        },
        {
            "code": "XiangHai",
            "name": "香海热电厂",
            "type": "热电厂",
            "baseAmount": 50000,
            "score": 96.50,
            "pendingCount": 0,
            "eligible": True,
            "disqualifyReason": "",
            "isBlackListed": False,
            "isRedListed": False,
            "hasMajorAccident": False,
            "hasGeneralAccident": False,
            "indicators": [
                {"name": "耗标煤总量", "weight": 30, "unit": "吨", "hasTarget": True, "targetValue": 40000, "actualValue": 39500, "score": 30.38, "calcType": "energy_saving", "sourceLabel": "月报表"},
                {"name": "厂内水耗量", "weight": 10, "unit": "吨", "hasTarget": True, "targetValue": 36000, "actualValue": 36500, "score": 9.86, "calcType": "consumption", "sourceLabel": "月报表"},
                {"name": "现货电价", "weight": 20, "unit": "元/MWh", "hasTarget": True, "targetValue": 234.63, "actualValue": 234.63, "score": 20.0, "calcType": "spot_price", "sourceLabel": "电力现货市场"},
                {"name": "全厂热效率", "weight": 20, "unit": "%", "hasTarget": True, "targetValue": 77.0, "actualValue": 75.5, "score": 16.10, "calcType": "efficiency", "sourceLabel": "月报表"},
                {"name": "非计划停炉停机", "weight": 10, "unit": "次", "hasTarget": False, "targetValue": 0, "actualValue": 0, "score": 10.0, "calcType": "shutdown", "sourceLabel": "手动填报"},
                None,
                {"name": "安全文明生产", "weight": 10, "unit": "分", "hasTarget": False, "targetValue": 10, "actualValue": 10.0, "score": 10.0, "calcType": "civic", "sourceLabel": "检查评定"},
            ],
        },
        {
            "code": "GongRe",
            "name": "供热公司",
            "type": "供热管网",
            "baseAmount": 60000,
            "score": 102.10,
            "pendingCount": 0,
            "eligible": True,
            "disqualifyReason": "",
            "isBlackListed": False,
            "isRedListed": True,
            "hasMajorAccident": False,
            "hasGeneralAccident": False,
            "indicators": [
                {"name": "主城区耗标煤总量", "weight": 20, "unit": "吨", "hasTarget": True, "targetValue": 110000, "actualValue": 108000, "score": 20.18, "calcType": "energy_saving_half", "sourceLabel": "月报表"},
                {"name": "供暖热单耗", "weight": 10, "unit": "GJ/万㎡", "hasTarget": True, "targetValue": 1800, "actualValue": 1750, "score": 10.28, "calcType": "consumption", "sourceLabel": "月报表"},
                {"name": "供暖电单耗", "weight": 15, "unit": "kWh/万㎡", "hasTarget": True, "targetValue": 3200, "actualValue": 3100, "score": 15.47, "calcType": "consumption", "sourceLabel": "月报表"},
                {"name": "供暖水单耗", "weight": 15, "unit": "t/万㎡", "hasTarget": True, "targetValue": 650, "actualValue": 640, "score": 15.23, "calcType": "consumption", "sourceLabel": "月报表"},
                {"name": "服务投诉率", "weight": 20, "unit": "件/万㎡", "hasTarget": False, "targetValue": 0, "actualValue": 0.082, "score": 20.0, "calcType": "complaint_rank", "complaintCount": 120, "heatingArea": 14634.15, "sourceLabel": "日报表"},
                {"name": "停供断管率", "weight": 10, "unit": "%", "hasTarget": True, "targetValue": 100, "actualValue": 100, "score": 10.0, "calcType": "pipe_cutoff", "sourceLabel": "手动填报"},
                {"name": "安全文明生产", "weight": 10, "unit": "分", "hasTarget": False, "targetValue": 10, "actualValue": 10.0, "score": 10.0, "calcType": "civic", "sourceLabel": "检查评定"},
            ],
        },
        {
            "code": "JinZhou",
            "name": "金州热电",
            "type": "热电分公司",
            "baseAmount": 50000,
            "score": 91.20,
            "pendingCount": 0,
            "eligible": True,
            "disqualifyReason": "",
            "isBlackListed": False,
            "isRedListed": False,
            "hasMajorAccident": False,
            "hasGeneralAccident": True,
            "indicators": [
                {"name": "耗标煤总量", "weight": 30, "unit": "吨", "hasTarget": True, "targetValue": 28000, "actualValue": 27500, "score": 30.54, "calcType": "energy_saving", "sourceLabel": "月报表"},
                {"name": "供暖电单耗", "weight": 15, "unit": "kWh/万㎡", "hasTarget": True, "targetValue": 3100, "actualValue": 3050, "score": 15.24, "calcType": "consumption", "sourceLabel": "月报表"},
                {"name": "供暖水单耗", "weight": 15, "unit": "t/万㎡", "hasTarget": True, "targetValue": 600, "actualValue": 590, "score": 15.25, "calcType": "consumption", "sourceLabel": "月报表"},
                {"name": "服务投诉率", "weight": 20, "unit": "件/万㎡", "hasTarget": False, "targetValue": 0, "actualValue": 0.105, "score": 18.0, "calcType": "complaint_rank", "complaintCount": 42, "heatingArea": 4000.0, "sourceLabel": "日报表"},
                {"name": "停供断管率", "weight": 10, "unit": "%", "hasTarget": True, "targetValue": 100, "actualValue": 100, "score": 10.0, "calcType": "pipe_cutoff", "sourceLabel": "手动填报"},
                None,
                {"name": "安全文明生产", "weight": 10, "unit": "分", "hasTarget": False, "targetValue": 10, "actualValue": 10.0, "score": 10.0, "calcType": "civic", "sourceLabel": "检查评定"},
            ],
        },
        {
            "code": "BeiFang",
            "name": "北方热电",
            "type": "热电分公司",
            "baseAmount": 30000,
            "score": 88.40,
            "pendingCount": 0,
            "eligible": False,
            "disqualifyReason": "投诉黑榜(取消资格)",
            "isBlackListed": True,
            "isRedListed": False,
            "hasMajorAccident": False,
            "hasGeneralAccident": False,
            "indicators": [
                {"name": "耗标煤总量", "weight": 30, "unit": "吨", "hasTarget": True, "targetValue": 18000, "actualValue": 18200, "score": 29.67, "calcType": "energy_saving", "sourceLabel": "月报表"},
                {"name": "供暖电单耗", "weight": 15, "unit": "kWh/万㎡", "hasTarget": True, "targetValue": 3000, "actualValue": 3020, "score": 14.90, "calcType": "consumption", "sourceLabel": "月报表"},
                {"name": "供暖水单耗", "weight": 15, "unit": "t/万㎡", "hasTarget": True, "targetValue": 550, "actualValue": 560, "score": 14.73, "calcType": "consumption", "sourceLabel": "月报表"},
                {"name": "服务投诉率", "weight": 20, "unit": "件/万㎡", "hasTarget": False, "targetValue": 0, "actualValue": 0.250, "score": 12.0, "calcType": "complaint_rank", "complaintCount": 30, "heatingArea": 1200.0, "sourceLabel": "日报表"},
                {"name": "停供断管率", "weight": 10, "unit": "%", "hasTarget": True, "targetValue": 100, "actualValue": 99.0, "score": 9.0, "calcType": "pipe_cutoff", "sourceLabel": "手动填报"},
                None,
                {"name": "安全文明生产", "weight": 10, "unit": "分", "hasTarget": False, "targetValue": 10, "actualValue": 8.1, "score": 8.1, "calcType": "civic", "sourceLabel": "检查评定"},
            ],
        },
        {
            "code": "JinPu",
            "name": "金普公司",
            "type": "供热分公司",
            "baseAmount": 10000,
            "score": 94.20,
            "pendingCount": 0,
            "eligible": True,
            "disqualifyReason": "",
            "isBlackListed": False,
            "isRedListed": False,
            "hasMajorAccident": False,
            "hasGeneralAccident": False,
            "indicators": [
                {"name": "耗标煤总量", "weight": 30, "unit": "吨", "hasTarget": True, "targetValue": 12000, "actualValue": 11900, "score": 30.25, "calcType": "energy_saving", "sourceLabel": "月报表"},
                {"name": "供暖电单耗", "weight": 15, "unit": "kWh/万㎡", "hasTarget": True, "targetValue": 2900, "actualValue": 2880, "score": 15.10, "calcType": "consumption", "sourceLabel": "月报表"},
                {"name": "供暖水单耗", "weight": 15, "unit": "t/万㎡", "hasTarget": True, "targetValue": 520, "actualValue": 515, "score": 15.14, "calcType": "consumption", "sourceLabel": "月报表"},
                {"name": "服务投诉率", "weight": 20, "unit": "件/万㎡", "hasTarget": False, "targetValue": 0, "actualValue": 0.130, "score": 16.0, "calcType": "complaint_rank", "complaintCount": 13, "heatingArea": 1000.0, "sourceLabel": "日报表"},
                {"name": "停供断管率", "weight": 10, "unit": "%", "hasTarget": True, "targetValue": 100, "actualValue": 100, "score": 10.0, "calcType": "pipe_cutoff", "sourceLabel": "手动填报"},
                None,
                {"name": "安全文明生产", "weight": 10, "unit": "分", "hasTarget": False, "targetValue": 10, "actualValue": 10.0, "score": 10.0, "calcType": "civic", "sourceLabel": "检查评定"},
            ],
        },
        {
            "code": "ZhuangHe",
            "name": "庄河环海",
            "type": "外购热供热",
            "baseAmount": 10000,
            "score": 89.00,
            "pendingCount": 0,
            "eligible": True,
            "disqualifyReason": "",
            "isBlackListed": False,
            "isRedListed": False,
            "hasMajorAccident": False,
            "hasGeneralAccident": False,
            "indicators": [
                {"name": "外购热量", "weight": 30, "unit": "GJ", "hasTarget": True, "targetValue": 180000, "actualValue": 179000, "score": 30.17, "calcType": "energy_saving", "sourceLabel": "月报表"},
                {"name": "供暖电单耗", "weight": 10, "unit": "kWh/万㎡", "hasTarget": True, "targetValue": 2600, "actualValue": 2610, "score": 9.96, "calcType": "consumption", "sourceLabel": "月报表"},
                {"name": "供暖水单耗", "weight": 20, "unit": "t/万㎡", "hasTarget": True, "targetValue": 500, "actualValue": 505, "score": 19.80, "calcType": "consumption", "sourceLabel": "月报表"},
                {"name": "服务投诉率", "weight": 20, "unit": "件/万㎡", "hasTarget": False, "targetValue": 0, "actualValue": 0.160, "score": 14.0, "calcType": "complaint_rank", "complaintCount": 8, "heatingArea": 500.0, "sourceLabel": "日报表"},
                {"name": "停供断管率", "weight": 10, "unit": "%", "hasTarget": True, "targetValue": 100, "actualValue": 100, "score": 10.0, "calcType": "pipe_cutoff", "sourceLabel": "手动填报"},
                None,
                {"name": "安全文明生产", "weight": 10, "unit": "分", "hasTarget": False, "targetValue": 10, "actualValue": 10.0, "score": 10.0, "calcType": "civic", "sourceLabel": "检查评定"},
            ],
        },
    ]


class CompetitionExportTests(unittest.TestCase):
    def test_generate_complete_3_sheet_workbook(self):
        payload = {
            "month": "2026-02",
            "month_label": "2026年02月",
            "status_note": "在线测算验收",
            "units_data": _sample_complete_units(),
        }
        xlsx_bytes, filename = generate_competition_excel(payload)

        self.assertEqual(filename, "供暖期指标竞赛考评表_2026-02.xlsx")
        self.assertGreater(len(xlsx_bytes), 5000)

        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=False)
        self.assertEqual(wb.sheetnames, ["考评兑现汇总", "指标得分矩阵", "计算过程明细"])

        # 1. 验证 Sheet 1: 考评兑现汇总
        ws_sum = wb["考评兑现汇总"]
        headers = [ws_sum.cell(row=4, column=c).value for c in range(1, 9)]
        self.assertEqual(
            headers,
            ["名次", "单位", "基数", "指标结果", "竞赛指标奖励金额", "其他嘉奖", "奖励合计", "资格状态（核查参考）"],
        )
        # 按分数降序：第1名应为供热公司 (102.10)，第2名为北海热电厂 (100.38)
        self.assertEqual(ws_sum["B5"].value, "供热公司")
        self.assertEqual(ws_sum["B6"].value, "北海热电厂")
        # 跨表引用得分与5元倍数取整公式
        self.assertEqual(ws_sum["D5"].value, "='指标得分矩阵'!G14")
        self.assertIn("ROUND((C5*D5/100)/5, 0)*5", ws_sum["E5"].value)
        self.assertEqual(ws_sum["G5"].value, "=E5+F5")
        # 合计行
        self.assertEqual(ws_sum["B12"].value, "合计")
        self.assertEqual(ws_sum["E12"].value, "=SUM(E5:E11)")
        self.assertIn("否决 1 家", ws_sum["H12"].value)
        # 黑榜被否决单位（北方热电 88.40，排在第7行=row 11）
        self.assertEqual(ws_sum["B11"].value, "北方热电")
        self.assertEqual(ws_sum["H11"].value, "投诉黑榜(取消资格)")

        # 2. 验证 Sheet 2: 指标得分矩阵
        ws_mat = wb["指标得分矩阵"]
        merged_coords = {str(rng) for rng in ws_mat.merged_cells.ranges}
        self.assertIn("A5:A10", merged_coords)
        self.assertIn("A11:A13", merged_coords)
        # 北海前两行合并 5~6，供热公司 5/6 拆分为主城区耗标煤总量+供暖热单耗
        self.assertIn("B5:B6", merged_coords)
        self.assertEqual(ws_mat["F5"].value, "主城区耗标煤总量")
        self.assertEqual(ws_mat["F6"].value, "供暖热单耗")
        self.assertEqual(ws_mat["B8"].value, "现货电价")
        self.assertEqual(ws_mat["B13"].value, "红黑榜奖惩")
        self.assertEqual(ws_mat["C14"].value, "=MAX(0, SUM(C5:C13))")
        self.assertTrue(str(ws_mat["C5"].value).startswith("=IF('计算过程明细'!"))

        # 3. 验证 Sheet 3: 计算过程明细
        ws_det = wb["计算过程明细"]
        all_texts = [ws_det.cell(row=r, column=c).value for r in range(1, ws_det.max_row + 1) for c in range(1, 12)]
        self.assertIn("附表：供热单位服务投诉率横向排名计算依据（5 家参评供热单位）", all_texts)
        self.assertTrue(any(isinstance(v, str) and v.startswith("=MAX(0, SUM(J") for v in all_texts))

    def test_pending_month_keeps_blank_actuals_as_none(self):
        units = _sample_complete_units()
        # 模拟 11 月月中：北海耗标煤总量仅有计划值、尚无月报实际值
        units[0]["pendingCount"] = 3
        units[0]["score"] = 42.20
        units[0]["indicators"][0]["actualValue"] = None
        units[0]["indicators"][0]["score"] = None

        xlsx_bytes, _ = generate_competition_excel(
            {
                "month": "2026-11",
                "month_label": "2026年11月（含启动考评）",
                "status_note": "自动取数完成（月报实际值尚未出数）",
                "units_data": units,
            }
        )
        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=False)
        ws_sum = wb["考评兑现汇总"]
        statuses = [ws_sum.cell(row=r, column=8).value for r in range(5, 12)]
        self.assertTrue(any("阶段测算（尚有3项待月报）" == s for s in statuses))

        ws_det = wb["计算过程明细"]
        # 找到北海耗标煤总量所在行，确认实际完成值为 None 且核算得分为 None、算式说明含“待月报发布”
        found_row = None
        for r in range(5, ws_det.max_row + 1):
            if ws_det.cell(row=r, column=1).value == "北海热电厂" and ws_det.cell(row=r, column=3).value == "耗标煤总量":
                found_row = r
                break
        self.assertIsNotNone(found_row)
        self.assertIsNone(ws_det.cell(row=found_row, column=6).value)
        self.assertIsNone(ws_det.cell(row=found_row, column=10).value)
        self.assertIn("月报尚未出数", str(ws_det.cell(row=found_row, column=9).value))

    def test_empty_units_raises_value_error(self):
        with self.assertRaises(ValueError):
            generate_competition_excel({"month": "2026-11", "units_data": []})

    def test_api_handler_returns_xlsx_streaming_response(self):
        req = ExportCompetitionExcelRequest(
            month="2026-02",
            month_label="2026年02月",
            status_note="接口测试",
            units_data=_sample_complete_units(),
        )
        resp = post_competition_export_excel(req)
        self.assertEqual(
            resp.media_type,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("filename*=UTF-8''", resp.headers.get("Content-Disposition", ""))

    def test_extra_rewards_populate_summary_and_detail_sheet(self):
        units = _sample_complete_units()
        units[0]["extraRewards"] = [
            {"title": "寒潮稳供专项嘉奖", "amount": 5000, "remark": "董事长专题会"},
            {"title": "机组运行创新奖", "amount": 2500, "remark": ""},
        ]
        xlsx_bytes, _ = generate_competition_excel(
            {
                "month": "2026-02",
                "month_label": "2026年02月",
                "status_note": "含额外嘉奖测算",
                "units_data": units,
            }
        )
        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=False)
        ws_sum = wb["考评兑现汇总"]
        # 北海热电厂排在第 2 行数据 (row=6)，F6 应为 7500
        self.assertEqual(ws_sum["B6"].value, "北海热电厂")
        self.assertEqual(ws_sum["F6"].value, 7500)
        summary_notes = [str(ws_sum.cell(row=r, column=1).value or "") for r in range(13, ws_sum.max_row + 1)]
        self.assertTrue(any("寒潮稳供专项嘉奖" in t for t in summary_notes))

        ws_det = wb["计算过程明细"]
        det_texts = [ws_det.cell(row=r, column=c).value for r in range(1, ws_det.max_row + 1) for c in range(1, 9)]
        self.assertIn("附表二：各单位额外嘉奖项目及金额明细（手动认定）", det_texts)
        self.assertIn("寒潮稳供专项嘉奖", det_texts)
        self.assertIn("机组运行创新奖", det_texts)
        self.assertTrue(any(isinstance(v, str) and v.startswith("=SUM(E") for v in det_texts))

    def test_manual_actual_coloring_and_annotation(self):
        units = _sample_complete_units()
        # 北海热电厂“耗标煤总量”和“安全文明生产”标记为人工调整，供热公司“服务投诉率”标记为人工调整
        units[0]["indicators"][0]["isManualActual"] = True
        civic_ind = next(i for i in units[0]["indicators"] if i and i.get("calcType") == "civic")
        civic_ind["isManualActual"] = True
        gongre = next(u for u in units if u["code"] == "GongRe")
        complaint_ind = next(i for i in gongre["indicators"] if i and i.get("calcType") == "complaint_rank")
        complaint_ind["isManualActual"] = True

        xlsx_bytes, _ = generate_competition_excel(
            {
                "month": "2026-02",
                "month_label": "2026年02月",
                "status_note": "人工调整着色测试",
                "units_data": units,
            }
        )
        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=False)
        ws_det = wb["计算过程明细"]

        # 第 3 行应显示浅琥珀色着色说明
        self.assertIn("浅琥珀色底纹", str(ws_det["A3"].value or ""))
        self.assertEqual(ws_det["A3"].fill.start_color.rgb, "00FEF3C7")

        # 北海耗标煤总量（第 5 行）与安全文明生产（第 10 行）的 F 列和 K 列应着色并标注【人工调整】
        self.assertEqual(ws_det["F5"].fill.start_color.rgb, "00FEF3C7")
        self.assertEqual(ws_det["K5"].fill.start_color.rgb, "00FEF3C7")
        self.assertIn("人工调整", str(ws_det["K5"].value or ""))

        civic_rows = [r for r in range(5, ws_det.max_row + 1) if ws_det.cell(row=r, column=1).value == "北海热电厂" and ws_det.cell(row=r, column=3).value == "安全文明生产"]
        self.assertEqual(len(civic_rows), 1)
        cr_row = civic_rows[0]
        self.assertEqual(ws_det.cell(row=cr_row, column=6).fill.start_color.rgb, "00FEF3C7")
        self.assertIn("人工调整", str(ws_det.cell(row=cr_row, column=11).value or ""))

        # 底部投诉率附表中供热公司的服务投诉率单元格（第 5 列）应着色
        app_rows = [
            r for r in range(5, ws_det.max_row + 1)
            if ws_det.cell(row=r, column=2).value == "供热公司" and isinstance(ws_det.cell(row=r, column=1).value, int)
        ]
        self.assertEqual(len(app_rows), 1)
        self.assertEqual(ws_det.cell(row=app_rows[0], column=5).fill.start_color.rgb, "00FEF3C7")


if __name__ == "__main__":
    unittest.main()
