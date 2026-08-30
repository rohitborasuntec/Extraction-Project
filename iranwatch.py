import asyncio,time,random
import pandas as pd
from playwright.async_api import async_playwright

url = "https://www.nj.gov/treasury/revenue/debarment/debarsearch-medical.shtml"


async def configurable_browser(playwright, headless=False, slow_mo=100):
    """Launch a browser with custom context settings and return browser, context, page."""
    browser = await playwright.chromium.launch(
        headless=headless,
        slow_mo=slow_mo,
        args=['--disable-blink-features=AutomationControlled']
    )

    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )

    page = await context.new_page()
    page.set_default_timeout(30000)

    return browser, context, page


async def parse_page(page):
    # Grab every table on the page — adjust selector if you know the exact one
    tables = await page.query_selector_all("//table[contains(@class, 'table-repsonsive')]//tbody//tr")
    print(tables)
    await asyncio.sleep(random.uniform(1, 3))
    all_rows = []
    breakpoint()
    for row in tables:
        # First row assumed to be header
        header_cells = await row.query_selector_all("td")
        row_data = {}
        row_data['Firm'] = await header_cells[0].inner_text()
        row_data['Category'] = await header_cells[1].inner_text()
        row_data['Action'] = await header_cells[2].inner_text()
        all_rows.append(row_data)

    return all_rows


async def authenticated_script():
    async with async_playwright() as p:
        browser, context, page = await configurable_browser(p)

        await page.goto(url)

        # Get all dropdown option values (skip the first blank option)
        select_element = await page.wait_for_selector("#srchreason", timeout=5000)
        option_values = await select_element.evaluate(
            "el => Array.from(el.options).map(opt => opt.value)"
        )
        option_values = option_values[1:]  # skip first blank <option value>

        results = {}

        for value in option_values:
            # Select the dropdown value
            await page.select_option("#srchreason", value)

            # Click the search button
            await page.click('input[value="Start Search"]')

            # Wait for results to load — adjust selector/timeout as needed
            await page.wait_for_load_state("networkidle")

            # Parse the results table
            rows = await parse_page(page)
            results[value] = rows

            # Go back to the search form for the next iteration
            await page.goto(url)
            await page.wait_for_selector("#srchreason", timeout=5000)

        await browser.close()
        return results


if __name__ == "__main__":
    results = asyncio.run(authenticated_script())
    pd.DataFrame.from_dict(results, orient='index').to_csv("debarment_results.csv", index=False)