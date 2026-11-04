// 工况一览展示顺序与原始采集键，依据 2026-11-04 用户提供的 HAR 页面。
// 展示名称可校正，sourceName 必须保留上游原文，不能套用热源信息分类 ID。
export const OVERVIEW_GROUPS = [
  {
    "title": "电厂参数",
    "rows": [
      {
        "no": 1,
        "name": "北海#1炉主汽",
        "sourceName": "北海#1炉主汽",
        "dictName": "dc_dict"
      },
      {
        "no": 2,
        "name": "北海#2炉主汽",
        "sourceName": "北海#2炉主汽",
        "dictName": "dc_dict"
      },
      {
        "no": 3,
        "name": "北海#3炉主汽",
        "sourceName": "北海#3炉主汽",
        "dictName": "dc_dict"
      },
      {
        "no": 4,
        "name": "北海#4炉主汽",
        "sourceName": "北海#4炉主汽",
        "dictName": "dc_dict"
      },
      {
        "no": 5,
        "name": "北海#1机进汽",
        "sourceName": "北海#1机进气",
        "dictName": "dc_dict"
      },
      {
        "no": 6,
        "name": "北海#2机进汽",
        "sourceName": "北海#2机进气",
        "dictName": "dc_dict"
      },
      {
        "no": 7,
        "name": "北海#3机右进汽",
        "sourceName": "北海3号机右主汽",
        "dictName": "dc_dict"
      },
      {
        "no": 8,
        "name": "北海#3机左进汽",
        "sourceName": "北海3号机左主汽",
        "dictName": "dc_dict"
      },
      {
        "no": 9,
        "name": "北海#3机抽汽",
        "sourceName": "北海#3机抽气",
        "dictName": "dc_dict"
      },
      {
        "no": 10,
        "name": "香海#1炉主汽",
        "sourceName": "香海1号炉主汽参数",
        "dictName": "dc_dict"
      },
      {
        "no": 11,
        "name": "香海#2炉主汽",
        "sourceName": "香海2号炉主汽参数",
        "dictName": "dc_dict"
      },
      {
        "no": 12,
        "name": "香海#3炉主汽",
        "sourceName": "香海3号炉主汽参数",
        "dictName": "dc_dict"
      },
      {
        "no": 13,
        "name": "香海#4炉主汽",
        "sourceName": "香海4号炉主汽参数",
        "dictName": "dc_dict"
      },
      {
        "no": 14,
        "name": "香海#1机主汽",
        "sourceName": "香海1号机主汽参数",
        "dictName": "dc_dict"
      },
      {
        "no": 15,
        "name": "香海#1机抽汽",
        "sourceName": "香海1号机抽汽参数",
        "dictName": "dc_dict"
      },
      {
        "no": 16,
        "name": "香海#2机主汽",
        "sourceName": "香海2号机主汽参数",
        "dictName": "dc_dict"
      },
      {
        "no": 17,
        "name": "香海#2机抽汽",
        "sourceName": "香海2号机抽汽参数",
        "dictName": "dc_dict"
      },
      {
        "no": 18,
        "name": "香海#3机主汽",
        "sourceName": "香海3号机主汽参数",
        "dictName": "dc_dict"
      },
      {
        "no": 19,
        "name": "香海#3机抽汽",
        "sourceName": "香海3号机抽汽参数",
        "dictName": "dc_dict"
      },
      {
        "no": 20,
        "name": "香海#4机进汽",
        "sourceName": "香海4号机进汽参数",
        "dictName": "dc_dict"
      },
      {
        "no": 21,
        "name": "香海#4机排汽",
        "sourceName": "香海4号机排气参数",
        "dictName": "dc_dict"
      },
      {
        "no": 22,
        "name": "北海#1水炉",
        "sourceName": "北首3#1号炉出口水",
        "dictName": "sz_dict"
      },
      {
        "no": 23,
        "name": "北海#2水炉",
        "sourceName": "北首3#2号炉出口水",
        "dictName": "sz_dict"
      },
      {
        "no": 24,
        "name": "北海#3水炉",
        "sourceName": "北首3#3号炉出口水",
        "dictName": "sz_dict"
      },
      {
        "no": 25,
        "name": "北海#1首站南环补",
        "sourceName": "南环补水",
        "dictName": "sz_dict"
      },
      {
        "no": 26,
        "name": "北海#1首站东环补",
        "sourceName": "东环补水",
        "dictName": "sz_dict"
      },
      {
        "no": 27,
        "name": "北海#2首站补水",
        "sourceName": "北2首_高温水补水",
        "dictName": "sz_dict"
      },
      {
        "no": 28,
        "name": "北海#3首站补水",
        "sourceName": "锅炉补水",
        "dictName": "sz_dict"
      }
    ]
  },
  {
    "title": "首站参数",
    "rows": [
      {
        "no": 1,
        "name": "北海#1首站东环供",
        "sourceName": "东环供水",
        "dictName": "sz_dict"
      },
      {
        "no": 2,
        "name": "北海#1首站东环回",
        "sourceName": "东环回水",
        "dictName": "sz_dict"
      },
      {
        "no": 3,
        "name": "北海#1首站南环供",
        "sourceName": "南环供水",
        "dictName": "sz_dict"
      },
      {
        "no": 4,
        "name": "北海#1首站南环回",
        "sourceName": "南环回水",
        "dictName": "sz_dict"
      },
      {
        "no": 5,
        "name": "北海#2首站供水",
        "sourceName": "北2首_高温水供水",
        "dictName": "sz_dict"
      },
      {
        "no": 6,
        "name": "北海#2首站回水",
        "sourceName": "北2首_高温水回水",
        "dictName": "sz_dict"
      },
      {
        "no": 7,
        "name": "北海水炉东环供水",
        "sourceName": "水炉东环热网供水",
        "dictName": "sz_dict"
      },
      {
        "no": 8,
        "name": "北海水炉东环回水",
        "sourceName": "水炉东环热网回水",
        "dictName": "sz_dict"
      },
      {
        "no": 9,
        "name": "北海水炉南环供水",
        "sourceName": "水炉南环热网供水",
        "dictName": "sz_dict"
      },
      {
        "no": 10,
        "name": "北海水炉南环回水",
        "sourceName": "水炉南环热网回水",
        "dictName": "sz_dict"
      },
      {
        "no": 11,
        "name": "北海厂界东环供水",
        "sourceName": "厂界东环热网供水",
        "dictName": "sz_dict"
      },
      {
        "no": 12,
        "name": "北海厂界东环回水",
        "sourceName": "厂界东环热网回水",
        "dictName": "sz_dict"
      },
      {
        "no": 13,
        "name": "北海厂界南环供水",
        "sourceName": "厂界南环热网供水",
        "dictName": "sz_dict"
      },
      {
        "no": 14,
        "name": "北海厂界南环回水",
        "sourceName": "厂界南环热网回水",
        "dictName": "sz_dict"
      },
      {
        "no": 15,
        "name": "中心区-北网联络供",
        "sourceName": "中心区-北网供",
        "dictName": "sz_dict"
      },
      {
        "no": 16,
        "name": "中心区-北网联络回",
        "sourceName": "中心区-北网回",
        "dictName": "sz_dict"
      },
      {
        "no": 17,
        "name": "香海首站供水",
        "sourceName": "香首_高温水供水",
        "dictName": "sz_dict"
      },
      {
        "no": 18,
        "name": "香海首站回水",
        "sourceName": "香首_高温水回水",
        "dictName": "sz_dict"
      }
    ]
  },
  {
    "title": "一网参数",
    "rows": [
      {
        "no": 1,
        "name": "北网混水供",
        "sourceName": "北网混水供",
        "dictName": "yw2_dict"
      },
      {
        "no": 2,
        "name": "北网混水回",
        "sourceName": "北网混水回",
        "dictName": "yw2_dict"
      },
      {
        "no": 3,
        "name": "中心区混水供(界)",
        "sourceName": "中心区混水供(界)",
        "dictName": "yw2_dict"
      },
      {
        "no": 4,
        "name": "中心区混水回(界)",
        "sourceName": "中心区混水回(界)",
        "dictName": "yw2_dict"
      },
      {
        "no": 5,
        "name": "中心区混水供",
        "sourceName": "中心区混水供",
        "dictName": "yw2_dict"
      },
      {
        "no": 6,
        "name": "双兴北",
        "sourceName": "双兴锅炉房",
        "dictName": "yw_dict"
      },
      {
        "no": 7,
        "name": "金广",
        "sourceName": "金广",
        "dictName": "yw_dict"
      },
      {
        "no": 8,
        "name": "机车西",
        "sourceName": "机车西山村区",
        "dictName": "yw_dict"
      },
      {
        "no": 9,
        "name": "盖州街",
        "sourceName": "盖州街",
        "dictName": "yw_dict"
      },
      {
        "no": 10,
        "name": "造船（北）",
        "sourceName": "造船新厂",
        "dictName": "sh_dict"
      },
      {
        "no": 11,
        "name": "造船（香）",
        "sourceName": "造船老厂（船舶重工）",
        "dictName": "sh_dict"
      }
    ]
  },
  {
    "title": "换热站及商户参数",
    "rows": [
      {
        "no": 1,
        "name": "香海#1低真空供",
        "sourceName": "香海1号机低真空供水",
        "dictName": "dc_dict"
      },
      {
        "no": 2,
        "name": "香海#1低真空回",
        "sourceName": "香海1号机低真空回水",
        "dictName": "dc_dict"
      },
      {
        "no": 3,
        "name": "香海#3低真空供",
        "sourceName": "香海3号机低真空供水",
        "dictName": "dc_dict"
      },
      {
        "no": 4,
        "name": "香海#3低真空回",
        "sourceName": "香海3号机低真空回水",
        "dictName": "dc_dict"
      },
      {
        "no": 5,
        "name": "北海南网",
        "sourceName": "北海南网",
        "dictName": "dc_dict"
      },
      {
        "no": 6,
        "name": "香海东网小",
        "sourceName": "香海东网蒸汽小",
        "dictName": "dc_dict"
      },
      {
        "no": 7,
        "name": "香海东网大",
        "sourceName": "香海东网蒸汽",
        "dictName": "dc_dict"
      },
      {
        "no": 8,
        "name": "香海西网小",
        "sourceName": "香海西网蒸汽小",
        "dictName": "dc_dict"
      },
      {
        "no": 9,
        "name": "香海西网大",
        "sourceName": "香海西网蒸汽",
        "dictName": "dc_dict"
      },
      {
        "no": 10,
        "name": "香-北联络",
        "sourceName": "香海-北海联络管",
        "dictName": "dc_dict"
      },
      {
        "no": 11,
        "name": "北海北网用户",
        "sourceName": "北海北网用户",
        "dictName": "yw2_dict"
      },
      {
        "no": 12,
        "name": "北海北网换热站",
        "sourceName": "北海北网换热站",
        "dictName": "yw2_dict"
      },
      {
        "no": 13,
        "name": "中心区用户",
        "sourceName": "中心区用户",
        "dictName": "yw2_dict"
      },
      {
        "no": 14,
        "name": "中心区换热站",
        "sourceName": "中心区换热站",
        "dictName": "yw2_dict"
      },
      {
        "no": 15,
        "name": "北海南网用户",
        "sourceName": "北海南网用户",
        "dictName": "yw2_dict"
      },
      {
        "no": 16,
        "name": "北海南网换热站",
        "sourceName": "北海南网换热站",
        "dictName": "yw2_dict"
      },
      {
        "no": 17,
        "name": "香海网用户",
        "sourceName": "香海网用户",
        "dictName": "yw2_dict"
      },
      {
        "no": 18,
        "name": "香海网换热站",
        "sourceName": "香海网换热站",
        "dictName": "yw2_dict"
      },
      {
        "no": 19,
        "name": "高温水用户汇总",
        "sourceName": "高温水用户汇总",
        "dictName": "yw2_dict"
      },
      {
        "no": 20,
        "name": "高温水站汇总",
        "sourceName": "高温水换热站汇总",
        "dictName": "yw2_dict"
      },
      {
        "no": 21,
        "name": "蒸汽用户汇总",
        "sourceName": "蒸汽用户汇总",
        "dictName": "yw2_dict"
      },
      {
        "no": 22,
        "name": "蒸汽站汇总",
        "sourceName": "蒸汽换热站汇总",
        "dictName": "yw2_dict"
      },
      {
        "no": 23,
        "name": "香海#1低真空补",
        "sourceName": "香海1号机低真空补水",
        "dictName": "dc_dict"
      },
      {
        "no": 24,
        "name": "香海#3低真空补",
        "sourceName": "香海3号机低真空补水",
        "dictName": "dc_dict"
      },
      {
        "no": 25,
        "name": "香海首站补水",
        "sourceName": "香首_高温水补水",
        "dictName": "sz_dict"
      }
    ]
  }
]

