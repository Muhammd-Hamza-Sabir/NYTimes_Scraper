#!/usr/bin/env python
# coding: utf-8

# In[41]:


import re
import os
import time
import json
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
import requests

from config import OUTPUT, search_phrase, news_category, num_months


# In[42]:


class NYTimesScraper:
    def __init__(self):
        #self.config = config
        self.OUTPUT = OUTPUT
        self.search_phrase = search_phrase
        self.news_category = news_category
        self.num_months = num_months
        self.date_pattern = r"/(\d{4}/\d{2}/\d{2})/"
        self.money_pattern = r'(\$\d+(\.\d+)?|\$\d{1,3}(,\d{3})*(\.\d+)?|\d+(\.\d+)? (dollars|USD))'
        self.df = pd.DataFrame()

        
    def subtract_months_from_current_date(self):
        current_date = datetime.now()
        new_date = current_date - relativedelta(months=self.num_months)
        return new_date

    
    def start_browser(self):
        path = "chromedriver"
        service = Service(path)
        return webdriver.Chrome(service=service)

    
    def navigate_to_site(self, driver, url):
        driver.get(url)

        
    def close_overlay(self, driver):
        try:
            overlay = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//div[@id="complianceOverlay"]/div[@class="css-hqisq1"]/button[@class="css-1fzhd9j"]')))
            overlay.click()
        except Exception as e:
            print("Error while closing overlay:", e)

            
    def enter_search_phrase(self, driver):
        try:
            driver.find_element(by='xpath', value='//div[@class="css-10488qs"]/button[@class="css-tkwi90 e1iflr850"]').click()
            search_box = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//div[@id="search-input"]/form[@action="/search"]/div[@class="css-1jl66k3"]/input[@data-testid="search-input"]')))
            search_box.send_keys(self.search_phrase)
            search_box.send_keys(Keys.RETURN)
        except NoSuchElementException as e:
            print("Error: Search box not found. Check if the website structure has changed.", e)

            
    def apply_filters(self, driver):
        try:
            # Wait for the sections to be present and click on the search-multiselect-button
            sections = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//button[@data-testid="search-multiselect-button"]')))
            sections.click()

            # Wait for the categories to be present and select the desired news_categories
            categories = driver.find_elements(by='xpath', value='//div[@class="css-tw4vmx"]/ul[@data-testid="multi-select-dropdown-list"]/li[@class="css-1qtb2wd"]/label[@class="css-1a8ayg6"]/span[@class="css-16eo56s"]')
            for cat in categories:
                # Use JavaScript to get the direct text content of the span element
                category_text = driver.execute_script('return arguments[0].firstChild.textContent', cat)
                if category_text in self.news_category:
                    cat.click()

            # Wait for the sorting dropdown to be present and click on it
            news_sorting = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//div[@class="css-hrdzfd"]')))
            news_sorting.click()

            # Now, select the 'newest' option from the sorting dropdown
            newest_option = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//select[@class="css-v7it2b"]/option[@value="newest"]')))
            newest_option.click()
            time.sleep(5)
        except Exception as e:
            print("Error while applying filters:", e)

            
    def extract_data(self, driver, end_date):
        try:
            # Wait for the search results to be present
            search_results = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, '//main[@id="site-content"]/div[@class="css-1wa7u5r"]/div/div[@class="css-46b038"]/ol[@data-testid="search-results"]')))
            articles = search_results[0].find_elements(by='xpath', value='//li[@class="css-1l4w6pd"]/div[@class="css-1kl114x"]')

            dates = []
            titles = []
            descriptions = []
            img_srcs = []
            for article in articles:
                url = article.find_element(by='xpath', value='.//div[@class="css-1i8vfl5"]/div[@class="css-e1lvw9"]/a').get_attribute("href")

                # Search for the date pattern in the URL and extract the date
                match = re.search(self.date_pattern, url)
                if match:
                    # Extracted date as string (e.g., "2023/07/22")
                    extracted_date_str = match.group(1)
                    # Convert the extracted date string into a datetime object
                    extracted_date = datetime.strptime(extracted_date_str, "%Y/%m/%d")

                    # Extract the title
                    title = article.find_element(by='xpath', value='.//div[@class="css-1i8vfl5"]/div[@class="css-e1lvw9"]/a/h4[@class="css-2fgx4k"]').text

                    # Extract the description if available
                    try:
                        description = article.find_element(by='xpath', value='.//div[@class="css-1i8vfl5"]/div[@class="css-e1lvw9"]/a/p[@class="css-16nhkrn"]').text
                    except NoSuchElementException:
                        description = ""

                    # Extract the image source
                    img_url = article.find_element(by='xpath', value='.//div[@class="css-1i8vfl5"]/figure[@class="css-tap2ym"]/div/img').get_attribute("src")
                    img_src = img_url[img_url.find('https://'):img_url.find('.jpg') + 4]

                    dates.append(extracted_date)
                    titles.append(title)
                    descriptions.append(description)
                    img_srcs.append(img_src)

            if len(dates) > 0:
                temp_df = pd.DataFrame({
                    "dates": dates,
                    "titles": titles,
                    "descriptions": descriptions,
                    "img_sources": img_srcs
                })
                self.df = pd.concat([self.df, temp_df], ignore_index=True)
                self.df = self.df.drop_duplicates()
            time.sleep(5)
        
        except Exception as e:
            print("Error while extracting data:", e)

            
    def show_more(self, driver):
        try:
            driver.find_element(by='xpath', value='//main[@id="site-content"]/div[@class="css-1wa7u5r"]/div/div[@class="css-1t62hi8"]/div[@class="css-vsuiox"]/button').click()
        except NoSuchElementException:
            pass

        
    def download_image(self, img_url):
        try:
            img_folder = os.path.join(self.OUTPUT, "downloaded_imgs")
            # Create a new folder named "downloaded_imgs" if it doesn't exist
            if not os.path.exists(img_folder):
                os.makedirs(img_folder)
                
            response = requests.get(img_url, stream=True)
            response.raise_for_status()

            # Get the filename from the URL (assumes the URL ends with .jpg or .png, adjust if necessary)
            file_name = img_url.split("/")[-1]

            # Combine the new folder path and filename
            file_path = os.path.join(img_folder, file_name)

            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            return file_path
        except Exception as e:
            print("Error while downloading image:", e)
            return None

        
    def contains_money(self, text):
        if text:
            return bool(re.search(self.money_pattern, text))
        return False

    
    def process_data(self):
        self.df['contains_money'] = self.df['titles'].str.cat(self.df['descriptions'], sep=' ').apply(self.contains_money)
        self.df['count_search_phrase'] = (self.df['titles'].str.contains(self.search_phrase, case=False).astype(int) +
                                          self.df['descriptions'].str.contains(self.search_phrase, case=False).astype(int))

    def save_to_excel(self):
        self.df.to_excel(os.path.join(self.OUTPUT, "nytimes_data.xlsx"), index=False)

        
    def run(self):
        try:
            driver = self.start_browser()
            self.navigate_to_site(driver, "https://www.nytimes.com/")
            self.close_overlay(driver)
            self.enter_search_phrase(driver)
            self.apply_filters(driver)
            
            end_date = self.subtract_months_from_current_date()
            self.extract_data(driver, end_date)
            
            while self.df.shape[0] > 0 and self.df['dates'].min() >= end_date:
                self.show_more(driver)
                time.sleep(5)
                self.extract_data(driver, end_date)

            driver.quit()
            if self.df.shape[0] > 0:
                self.process_data()
                self.save_to_excel()

            for img_url in self.df["img_sources"].values:
                self.download_image(img_url)
                
        except Exception as e:
            print("Error during execution:", e)


# In[ ]:


if __name__ == "__main__":

    # # Determine the path to the config.json file
    # config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "config.json")

    # # Read JSON data from the file
    # with open(config_file_path, "r") as file:
    #     config_data = json.load(file)


    scraper = NYTimesScraper()
    scraper.run()





