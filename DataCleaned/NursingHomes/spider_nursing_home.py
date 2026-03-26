from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os  # 引入os库用于检测文件是否存在


def scrape_city_data(city_name, city_code, max_pages=4):
    """
    抓取指定城市的养老院数据
    :param city_name: 城市名称（用于保存到csv中区分）
    :param city_code: URL中的RgSelect代码
    :param max_pages: 抓取得最大页数
    """
    print(f"\n====== 正在启动抓取任务：{city_name} (代码: {city_code}) ======")

    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument('--ignore-certificate-errors')

    # 每次调用都启动一个新的浏览器实例，防止缓存干扰
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    city_data = []

    try:
        for page in range(1, max_pages + 1):
            # 动态构建 URL，使用传入的 city_code
            url = f"https://www.yanglaocn.com/yanglaoyuan/yly/?RgSelect={city_code}&page={page}"
            print(f"正在访问第 {page} 页: {url}")

            driver.get(url)
            time.sleep(5)

            # 滑动验证检测
            if "安全" in driver.title or "验证" in driver.title:
                print(f"【注意！】在抓取 {city_name} 时检测到滑动验证。")
                input("请手动完成滑动后，按【回车键】继续...")
                time.sleep(3)

            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            items = soup.find_all('div', class_='jiadiantucontext')
            print(f"  -> 成功获取！本页发现 {len(items)} 条数据")

            if not items:
                print(f"  -> 警告：{city_name} 第 {page} 页无数据，可能已达末页。")
                break  # 如果某一页没数据，通常后面也没了，直接跳出翻页循环

            for item in items:
                try:
                    name = "未知名称"
                    title_area = item.select_one('.jiadiantulist ul:first-child li')
                    if title_area:
                        name = title_area.get_text(strip=True)

                    price_tag = item.select_one('.jiadiantujianjie_price strong')
                    price = price_tag.get_text(strip=True) if price_tag else "价格面议"

                    nature = "未知"
                    address = "未知"
                    bed_count = "未知"

                    details_div = item.find('div', class_='jiadiantulist')
                    if details_div:
                        li_list = details_div.find_all('li')
                        for li in li_list:
                            text = li.get_text(strip=True)
                            if "性质：" in text:
                                label = li.find('label', string='性质：')
                                if label and label.next_sibling:
                                    nature = label.next_sibling.strip()
                            if "地址：" in text:
                                label = li.find('label', string='地址：')
                                if label and label.next_sibling:
                                    address = label.next_sibling.strip()
                            if "床位：" in text:
                                label = li.find('label', string='床位：')
                                if label and label.next_sibling:
                                    bed_count = label.next_sibling.strip()

                    # 特色服务提取
                    tags = []
                    tag_elements = item.select('.el-tag')
                    for tag in tag_elements:
                        tag_text = tag.get_text(strip=True)
                        if tag_text:
                            tags.append(tag_text)
                    features_str = ",".join(tags)

                    city_data.append({
                        '城市': city_name,  # 新增字段：标记数据来源城市
                        '名称': name,
                        '性质': nature,
                        '床位': bed_count,
                        '价格(元/月)': price,
                        '特色服务': features_str,
                        '地址': address
                    })
                except Exception as e:
                    print(f"解析出错: {e}")

            time.sleep(random.uniform(2, 4))

    except Exception as e:
        print(f"抓取 {city_name} 时发生错误: {e}")
    finally:
        driver.quit()

    return city_data


def save_to_csv_append(data, filename='nursing_homes_all.csv'):
    """
    将数据追加到CSV文件中
    """
    if not data:
        print("无数据需要保存。")
        return

    df = pd.DataFrame(data)

    # 检查文件是否存在
    file_exists = os.path.exists(filename)

    # mode='a' 表示追加模式
    # header=not file_exists 表示：如果文件不存在(是新文件)，则写入表头；如果文件已存在，则不写表头
    df.to_csv(filename, mode='a', index=False, header=not file_exists, encoding='utf-8-sig')

    print(f"已成功追加 {len(df)} 条数据到 {filename}")


if __name__ == "__main__":
    # === 在这里配置你想抓取的城市列表 ===
    # 格式： {"城市名": "URL参数RgSelect的值"}
    # 这些代码来自网页源码 source: 42
    cities_to_scrape = {
        "北京": "01001",
        "上海": "02101",
        "福州": "059101",
        "重庆": "02301",
        "广州": "075501",
        "成都": "081301",
        "杭州": "057001",
        "海口":"089801",
        "武汉":"071401",
        "西安":"091401",
        "南京":"051001",
        "郑州":"037601",
        "昆明":"088801",
        "南宁":"077101",
        "贵阳":"085101"
    }

    # 循环抓取
    for city_name, city_code in cities_to_scrape.items():
        # 1. 抓取数据
        data = scrape_city_data(city_name, city_code, max_pages=4)  # 这里设置抓取每座城市的前2页用于测试

        # 2. 追加保存
        save_to_csv_append(data, filename='nursing_homes_all.csv')

        # 城市间稍作休息
        print(f"{city_name} 抓取完成，休息 3 秒...")
        time.sleep(3)

    print("\n所有城市抓取任务结束！请查看 nursing_homes_all.csv")