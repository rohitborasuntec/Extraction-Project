from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import random,time
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

driver = webdriver.Chrome()

columns = [
    "Name of Entity"," Alias Name"," Article number"," Order date"," Action Taken"," Source Link"
]
results_df = pd.DataFrame(columns=columns)
# def parse_page(driver):
#     tables = driver.find_elements(By.XPATH,"//table[contains(@class, 'table-repsonsive')]//tbody//tr")
#     print(tables)
#     # breakpoint()
#     all_rows = []
#     for row in tables:
        
#         header_cells = row.find_elements_by_tag_name("td")
#         row_data = {}
#         row_data['Firm'] = header_cells[0].text
#         row_data['Category'] = header_cells[1].text
#         row_data['Action'] = header_cells[2].text
#         all_rows.append(row_data)

#     return all_rows
def random_scroll(driver, min_scroll=200, max_scroll=800, min_pause=0.5, max_pause=2, iterations=None):
    """Random scroll to avoid detection"""
    if iterations is None:
        iterations = random.randint(5, 15)
    
    for _ in range(iterations):
        direction = 1 if random.random() < 0.8 else -1
        pixels = random.randint(min_scroll, max_scroll) * direction
        try:
            driver.execute_script("window.scrollBy({top: arguments[0], behavior: 'smooth'});", pixels)
        except:
            pass
        time.sleep(random.uniform(min_pause, max_pause))


def scrapping_name_data():
    print("Starting to scrape name data...")
    name_datas = driver.find_elements(By.XPATH,'//tr[contains(@class,"k-master-row")]//td[@role="gridcell"]')
    print(f"Found {len(name_datas)} total grid cells")
    
    names = []
    i = 1
    print("Processing names from grid cells...")
    while(i < len(name_datas)):
        name_text = name_datas[i].text
        names.append(name_text)
        print(f"Scrapped: {name_text} (Index: {i})")
        i += 2
    
    print(f"Successfully scrapped {len(names)} names")
    print("-" * 50)
    return names


def scrapping_pdf_details():
    print("Starting to scrape PDF details...")
    details = driver.find_elements(By.XPATH,'//tr[@class="k-detail-row"]//tbody[@role="rowgroup"]/tr')
    print(f"Found {len(details)} detail rows")
    
    action = []
    dates = []
    links = []
    
    for idx, detail in enumerate(details, 1):
        print(f"\nProcessing detail row {idx}/{len(details)}...")
        elems = detail.find_elements(By.XPATH,'./td')
        print(f"Found {len(elems)} columns in this row")
        
        action_text = elems[1].text
        date_text = elems[2].text
        action.append(action_text)
        dates.append(date_text)
        print(f"  Action: {action_text}")
        print(f"  Order date: {date_text}")
        # Extracting PDF link
        try:
            pdf_div = elems[3].find_element(By.XPATH,'.//div[@class="pdf-link"]')
            onclick_attr = pdf_div.get_attribute('onclick')
            print(f"  Onclick attribute: {onclick_attr}")
            
            id = onclick_attr.split("'")[1]
            print(f"Extracted ID: {id}")
            
            link = f"https://www.ldi.la.gov/OnlineServices/RegulatoryActions/home/viewattachment?id={id}&filename=viewattachment.pdf"
            links.append(link)
            print(f"  Generated PDF link: {link}")
        except Exception as e:
            print(f"  Error extracting PDF link: {e}")
            links.append("N/A")
    
    print(f"\nSuccessfully scrapped {len(action)} actions, {len(dates)} dates, and {len(links)} links")
    print("-" * 50)
    return action, dates, links

def authenticated_script():
    results = {}
    min_scroll = 30
    max_scroll = 50
    try:
        driver.get("https://www.ldi.la.gov/OnlineServices/RegulatoryActions")
        time.sleep(random.uniform(5, 12))
        # Find and click search button
        # wait = WebDriverWait(driver, 10)
        # elements = driver.find_elements(By.XPATH , '//ul[@id="regulatoryActionBar"]/li')
        # rows = {}
        # for element in elements[:1]:
        #     element.click()
        #     time.sleep(random.uniform(3,5))
        #     name_elements = driver.find_elements(By.XPATH , '//tbody[@role="rowgroup"]/tr') 
        #     for name_element in name_elements:
        #         name_element.find_element(By.XPATH,'.//a').click()
        #         # random_scroll(driver, min_scroll=min_scroll, max_scroll=max_scroll, min_pause=3, max_pause=5, iterations=1)
        #         # min_scroll += 20
        #         # max_scroll += 20
        #         time.sleep(random.uniform(3,8))
                # other_elems = name_element.find_elements(By.XPATH,'.//tbody[@role="rowgroup"]/tr/td')
                # for other_elem in other_elems:
                #     rows['']
                # ids = driver.find_elements(By.XPATH,'//div[@class="pdf-link"]')
                # for id in ids:
                #     id = id.get_attribute('onclick').split("'")[1]
                #     link = f"https://www.ldi.la.gov/OnlineServices/RegulatoryActions/home/viewattachment?id={id}&filename=viewattachment.pdf" 
                #     print(f"Link : {link}")
                #     results_df["Source Link"] = link

        # breakpoint()
                # name_element.click()
                # time.sleep(random.uniform(3,5))
        # results['URL'] = rows
        # return results
        # time.sleep(random.uniform(1, 2))
        
    except Exception as e:
        print(f"Critical error: {e}")
        results['error'] = str(e)
    
    # return results
columns = [
    "Name of Entity","Alias Name","Article number","Order date"," Action Taken","Source Link"
]
if __name__ == "__main__":
    print("=" * 60)
    print("STARTING DEBARMENT DATA SCRAPING PROCESS")
    print("=" * 60)
    
    # Uncomment if you need authentication
    # print("Running authentication script...")
    results = authenticated_script()
    print("Authentication completed")
    breakpoint()
    
    print("\nStep 1: Scraping entity names...")
    
    print("\nStep 2: Scraping PDF details (actions, dates, and links)...")
    action, dates, links = scrapping_pdf_details()
    results_df["Name of Entity"] = scrapping_name_data()[:len(action)]
    results_df["Action"] = action
    results_df["Order date"] = dates
    results_df["Source Link"] = links
    
    print("\nStep 3: Saving data to CSV...")
    csv_filename = "debarment_results.csv"
    results_df.to_csv(csv_filename, index=False)
    print(f"Data successfully saved to {csv_filename}")
    print(f"Total records saved: {len(results_df)}")
    
    print("\n" + "=" * 60)
    print("SCRAPING PROCESS COMPLETED SUCCESSFULLY")
    print("=" * 60)