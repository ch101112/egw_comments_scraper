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
from concurrent.futures import ThreadPoolExecutor


# ==============================================================================
# SETTINGS
# ==============================================================================

YEAR = "2021"
QUARTER = "03"  # 1...4
LANGUAGE = "en"  # "en" (default), "de", "fr"
NUM_FILES = 13  # 1...13 (default)
URL_ROOT = "https://sabbath-school.adventech.io/"


# ==============================================================================
# DEFINE SCRAPING FUNCTION
# ==============================================================================


def getTextWeek(baseUrl: str, weekNum: int, pathOutput) -> None:

    # Settings for Different Languages
    if LANGUAGE == "en":
        id = "additional-reading-selected-quotes-from-ellen-g-white"
        header = "h4"
        babel = "english"
    elif LANGUAGE == "fr":
        id = "citations-dellen-white-en-complément-à-létude-de-la-bible-par-lécole-du-sabbat"
        header = "h3"
        babel="french"
    elif LANGUAGE == "de":
        id = "zusätzliche-lektüre-ausgewählte-zitate-von-ellen-g-white"
        header = "h4"
        babel = "ngerman"
    else:
        raise ("Language not supported!!!")

    # Get Sabbath School Quarterly Title
    page = requests.get(baseUrl)
    soup = BeautifulSoup(page.content, "html.parser")
    titleQuarter = soup.select("h1")[0].text.strip()

    # Get Week Page
    urlWeek = f"{baseUrl}{weekNum:02}/01"
    pageWeek = requests.get(urlWeek)
    soupWeek = BeautifulSoup(pageWeek.content, "html.parser")

    # Get First Day of Week Page
    urlWeekFirstDay = soupWeek.select("title")[0].text.strip()
    pageWeekFirstDay = requests.get(urlWeekFirstDay)
    soupWeekFirstDay = BeautifulSoup(pageWeekFirstDay.content, "html.parser")

    # Get ToC Menu
    mydivs = soupWeekFirstDay.find_all("div", {"class": "ss-menu"})

    titleWeek = soupWeekFirstDay.select("h1")[0].text.strip()
    filename = os.path.join(pathOutput, f"egw_{LANGUAGE}_{weekNum:02}.tex")
    date = f"{YEAR}/{QUARTER} {titleQuarter}"

    # Open File
    f = open(filename, "w", encoding="utf-8")

    # Format the LaTeX-File
    f.write("\\documentclass[a4paper, 10pt, twoside, headings=small]{scrartcl}\n\n")
    f.write("\\input{../options.tex}\n\n")
    f.write("\\setmainlanguage[]{" + f"{babel}" + "}\n\n")
    f.write("\\title{" + f"{weekNum:02} {titleWeek}" + "}\n\n")
    f.write("\\author{Ellen G.\\ White}\n\n")
    f.write("\\date{" + f"{date}" + "}\n\n")
    f.write("\\begin{document}\n\n")
    f.write("\\maketitle\n\n")
    f.write("\\thispagestyle{empty}\n\n")
    f.write("\\pagestyle{fancy}\n\n")
    f.write("\\begin{multicols}{2}\n\n")

    # Get Links of Weekdays
    myAs = mydivs[0].select("a")
    
    def getDaySoups(a):
        urlDay = URL_ROOT[:-1] + a.get("href")
        pageDay = requests.get(urlDay)
        return BeautifulSoup(pageDay.content, "html.parser")
    
    # Get Daily soups
    with ThreadPoolExecutor(7) as ex:
        futures = [ex.submit(getDaySoups, a) for a in myAs[0:7]]
        soupsDay = [f.result() for f in futures]

    # Write to File
    for soupDay in soupsDay:
        try:
            titleEgw = soupDay.find(id=id).text.strip()
            titleMain = soupDay.select("h1")[0].text.strip()
            date = datetime.strptime(soupDay.select("time")[0].text.strip(), "%d/%m/%Y")

            # Write Day Section
            f.write(
                "\\section*{"
                + f"{format_datetime(date, format='EEEE', locale=LANGUAGE).capitalize()} – {titleMain}"
                + "}\n\n"
            )

            # No Indentation for Friday Paragraph
            if date.isoweekday() == 5:
                f.write("\\setlength{\parindent}{0pt}")
            
            # Select and Write the Paragraphs
            target = soupDay.find(header, text=titleEgw)
            for sib in target.find_next_siblings():
                if sib.name == header:
                    break
                else:
                    f.write(f"{sib.text}\n\n")
        except:
            print("No EGW comments for this day!")

    # Additional LaTeX Formatting
    f.write("\\end{multicols}\n\n")
    f.write("\\end{document}\n\n")
    f.close()
    print(f"File 'egw_{LANGUAGE}_{weekNum:02}.tex' written.")
    

# ==============================================================================
# RUN
# ==============================================================================

if __name__ == "__main__":

    # Create Local Output Folder
    try:
        os.mkdir("output")
    except:
        pass

    # Settings
    baseUrl = f"{URL_ROOT}{LANGUAGE}/{YEAR}-{QUARTER}/"
    locale.setlocale(locale.LC_TIME, LANGUAGE)
    pathOutput = os.path.join(os.path.abspath(os.getcwd()), "output")

    # Iterators for Multiprocessing Function Argument
    listLessons = list(range(1, 1 + NUM_FILES))
    listUrls = list(itertools.repeat(baseUrl, NUM_FILES))
    listPathOutput = list(itertools.repeat(pathOutput, NUM_FILES))

    # ----------------------
    # Scraping (in parallel)
    

    print("\n\n=====", "Scraping and saving the data to TeX-files...", "=====")

    t1 = time.time()
    with multiprocessing.Pool(min(int(multiprocessing.cpu_count()), NUM_FILES)) as p:
        for result in p.starmap(
            getTextWeek, zip(listUrls, listLessons, listPathOutput)
        ):
            pass
    print(f"Elapsed time (scraping): {time.time() - t1:.2f} s")

    # --------------------------
    # Compilation (sequentially)

    print("\n\n=====", "Compiling TeX-files. Can take a long time...", "=====")

    t1 = time.time()
    for i in range(1, 1 + NUM_FILES):
        filename = os.path.join(pathOutput, f"egw_{LANGUAGE}_{i:02}.tex")
        subprocess.call(
            f"xelatex {filename} -quiet -interaction=batchmode -output-directory {pathOutput} -halt-on-error "
        )
        print(f"File 'egw_{LANGUAGE}_{i:02}.tex' compiled.")
    print(f"Elapsed time (compilation): {time.time() - t1:.2f} s")
