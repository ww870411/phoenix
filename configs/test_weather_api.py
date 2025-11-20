import requests
import json
from datetime import datetime

# Open-Meteo API URL provided by the user
API_URL = "https://api.open-meteo.com/v1/forecast?latitude=38.875&longitude=121.625&hourly=temperature_2m&timezone=Asia%2FSingapore&past_days=3"

def fetch_and_print_temperature_data():
    """
    Fetches hourly temperature data from Open-Meteo API and prints it.
    """
    print(f"尝试从 Open-Meteo API 获取数据: {API_URL}")
    try:
        response = requests.get(API_URL)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)

        data = response.json()

        if "hourly" in data and "time" in data["hourly"] and "temperature_2m" in data["hourly"]:
            times = data["hourly"]["time"]
            temperatures = data["hourly"]["temperature_2m"]

            print("\n成功获取气温数据:")
            for i in range(len(times)):
                # Optional: Format time for better readability
                try:
                    dt_object = datetime.fromisoformat(times[i])
                    formatted_time = dt_object.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    formatted_time = times[i] # Fallback if time format is unexpected

                print(f"时间: {formatted_time}, 温度: {temperatures[i]} °C")
        else:
            print("API 响应中未找到 'hourly' 或 'time'/'temperature_2m' 数据。")
            print("完整响应内容:")
            print(json.dumps(data, indent=2))

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP 错误发生: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"连接错误发生: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"请求超时: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求发生未知错误: {req_err}")
    except json.JSONDecodeError as json_err:
        print(f"JSON 解析错误: {json_err}")
        # Assuming 'response' object exists from a successful request but bad JSON
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"原始响应文本: {response.text}")
    except Exception as e:
        print(f"发生意外错误: {e}")

if __name__ == "__main__":
    fetch_and_print_temperature_data()
