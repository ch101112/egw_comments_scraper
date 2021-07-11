import requests
from datetime import datetime
import locale
from bs4 import BeautifulSoup
import multiprocessing
import time
import os
import itertools
import subprocess
from babel.dates import format_datetime

# %% SETTINGS

YEAR = "2021"
QUARTER = "03"  # 1...4
LANGUAGE = "en"  # "en" (default), "de", "fr"
NUM_FILES = 1  # 1...13 (default)
URL_ROOT = "https://sabbath-school.adventech.io/"

# %% SCRAPER FUNCTION

def getTextWeek(baseUrl: str, weekNum: int, pathOutput) -> None:

    # Get Sabbath School Quarterly Title
    page = requests.get(baseUrl)
    soup = BeautifulSoup(page.content, "html.parser")
    titleQuarter = soup.select('h1')[0].text.strip()

    urlWeek = f"{baseUrl}{weekNum:02}/01"
    pageWeek = requests.get(urlWeek)
    soupWeek = BeautifulSoup(pageWeek.content, "html.parser")

    urlWeekFirstDay = soupWeek.select("title")[0].text.strip()
    pageWeekFirstDay = requests.get(urlWeekFirstDay)
    soupWeekFirstDay = BeautifulSoup(pageWeekFirstDay.content, "html.parser")

    mydivs = soupWeekFirstDay.find_all("div", {"class": "ss-menu"})
    titleWeek = soupWeekFirstDay.select("h1")[0].text.strip()

    filename = os.path.join(pathOutput, f"egw_{LANGUAGE}_{weekNum:02}.tex")

    f = open(filename, "w", encoding="utf-8")

    f.write(
        "\\documentclass[a4paper, 10pt, twoside, headings=small]{scrartcl}\n\n"
    )
    f.write("\\input{../options.tex}\n\n")
    f.write("\\title{" + f"{weekNum:02} {titleWeek}" + "}\n\n")
    f.write("\\author{Ellen G.\\ White}\n\n")
    date = f"{YEAR}/{QUARTER} {titleQuarter}"
    f.write("\\date{" + f"{date}" + "}\n\n")

    f.write("\\begin{document}\n\n")
    f.write("\\maketitle\n\n")
    f.write("\\thispagestyle{empty}\n\n")

    f.write("\\pagestyle{fancy}\n\n")
    f.write("\\begin{multicols}{2}\n\n")

    for div in mydivs:
        myAs = div.select("a")

        for k in range(0, 7):
            urlDay = URL_ROOT[:-1] + myAs[k].get("href")

            pageDay = requests.get(urlDay)
            soupDay = BeautifulSoup(pageDay.content, "html.parser")

            if LANGUAGE == "en":
                id = "additional-reading-selected-quotes-from-ellen-g-white"
                header = "h4"
            elif LANGUAGE == "fr":
                id = u"citations-dellen-white-en-complément-à-létude-de-la-bible-par-lécole-du-sabbat"
                header = "h3"
            elif LANGUAGE == "de":
                id = u"zusätzliche-lektüre-ausgewählte-zitate-von-ellen-g-white"
                header = "h4"
            else:
                raise ("Language not supported!!!")
            

            try:
                titleEgw = soupDay.find(id=id).text.strip()

                titleMain = soupDay.select("h1")[0].text.strip()
                date = datetime.strptime(
                    soupDay.select("time")[0].text.strip(), "%d/%m/%Y")

                f.write(
                    "\\section*{" +
                    f"{format_datetime(date, format='EEEE', locale=LANGUAGE).capitalize()} – {titleMain}"
                    + "}\n\n")

                if k == 6:  # changed parindent for firday
                    f.write("\\setlength{\parindent}{0pt}")

                target = soupDay.find(header, text=titleEgw)

                for sib in target.find_next_siblings():
                    if sib.name == header:
                        break
                    else:
                        f.write(f"{sib.text}\n\n")
            except:
                print("No EGW comments for this day!")

    f.write("\\end{multicols}\n\n")
    f.write("\\end{document}\n\n")
    f.close()
    print(f"File 'egw_{LANGUAGE}_{weekNum:02}.tex' written.")


# %% RUN

if __name__ == "__main__":
    
    try:
        os.mkdir("output")
    except:
        pass
    
    baseUrl = f"{URL_ROOT}{LANGUAGE}/{YEAR}-{QUARTER}/"
    locale.setlocale(locale.LC_TIME, LANGUAGE)
    pathOutput = os.path.join(os.path.abspath(os.getcwd()), "output")

    listLessons = list(range(1, 1 + NUM_FILES))
    listUrls = list(itertools.repeat(baseUrl, NUM_FILES))
    listPathOutput = list(itertools.repeat(pathOutput, NUM_FILES))

    # ----------------------
    # Scraping (in parallel)

    print("\n\n=====", "Scraping and saving the data to TeX-files...", "=====")

    t1 = time.time()
    with multiprocessing.Pool(min(int(multiprocessing.cpu_count()), NUM_FILES)) as p:
        for result in (p.starmap(getTextWeek,
                                 zip(listUrls, listLessons, listPathOutput))):
            pass
    print(f"Elapsed time (scraping): {time.time() - t1}")


    # --------------------------
    # Compilation (sequentially)

    print("\n\n=====", "Compiling TeX-files. Can take a long time...", "=====")

    t1 = time.time()
    for i in range(1, 1 + NUM_FILES):
        filename = os.path.join(pathOutput, f"egw_{LANGUAGE}_{i:02}.tex")
        subprocess.call(
            f"pdflatex.exe {filename} -quiet -interaction=batchmode -output-directory {pathOutput} -halt-on-error "
        )
        print(f"File 'egw_{LANGUAGE}_{i:02}.tex' compiled.")
    print(f"Elapsed time (compilation): {time.time() - t1}")