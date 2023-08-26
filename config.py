import os

OUTPUT = f"{os.getcwd()}/output"

search_phrase = "AI"
news_category = ["Technology"]
num_months = 1


def create_dir(path):
    if not os.path.exists(path):
        os.mkdir(path)
