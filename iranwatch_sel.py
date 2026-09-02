from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import random,time
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

driver = webdriver.Chrome()

def parse_page(driver):
    tables = driver.find_elements(By.XPATH,"//table[contains(@class, 'table-repsonsive')]//tbody//tr")
    print(tables)
    # breakpoint()
    all_rows = []
    for row in tables:
        
        header_cells = row.find_elements_by_tag_name("td")
        row_data = {}
        row_data['Firm'] = header_cells[0].text
        row_data['Category'] = header_cells[1].text
        row_data['Action'] = header_cells[2].text
        all_rows.append(row_data)

    return all_rows

def authenticated_script():
    results = {}
    
    try:
        driver.get("https://www.nj.gov/treasury/revenue/debarment/debarsearch-medical.shtml")
        time.sleep(random.uniform(1, 3))
        # Find and click search button
        wait = WebDriverWait(driver, 10)

        search_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[value="Start Search"]'))
        )
        search_button.click()

        rows = parse_page(driver)
        # results] = rows
        
        time.sleep(random.uniform(1, 2))
        
    except Exception as e:
        print(f"Critical error: {e}")
        results['error'] = str(e)
    
    # return results

if __name__ == "__main__":
    results = authenticated_script()
    pd.DataFrame.from_dict(results, orient='index').to_csv("debarment_results.csv", index=False)