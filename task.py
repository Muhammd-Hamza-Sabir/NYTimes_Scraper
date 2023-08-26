from scraper import NYTimesScraper
from config import OUTPUT, create_dir


if __name__ == "__main__":
    create_dir(OUTPUT)

    scraper = NYTimesScraper()
    scraper.run()