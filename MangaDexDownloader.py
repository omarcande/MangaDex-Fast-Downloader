import PIL.Image
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import requests
from urllib.request import urlopen
import json
import ssl
from io import BytesIO
from tkinter import *
from tkinter import messagebox
from tkinter.filedialog import askdirectory
import customtkinter
import os
import ctypes
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
import re
import zipfile
import glob
from ratelimit import limits, sleep_and_retry
import xml.etree.ElementTree as ET
import subprocess

myappid = 'frnono.manga.downloader'
if os.name == 'nt':
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

ssl._create_default_https_context = ssl._create_unverified_context

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("Theme/pink.json")
print("Short instructions\n")
print("For batch download, insert the manga id in the field, then press batch")
print("You can write the chapters where you want it to start and end")
print("If you input nothing or something invalid, it will download everything")
print("To download a single chapter, insert the chapter id in the field, then press go\n")

print(f"Ex: https://mangadex.org/title/ ---> e7eabe96-aa17-476f-b431-2497d5e9d060 <--- /black-clover\n")

print("PDF(fast) is a lot faster, as the name implies. If you want the PDF format, use this option")
print("PDF(slow) is pretty much useless, in some rare cases it looks better (a LOT slower)")
print("CBZ is probably the ideal format if you have a dedicated reader\n")

path = f"{os.environ['UserProfile']}/Downloads/" if os.name == 'nt' else "/tmp/"
mangadex_api = r"https://api.mangadex.org/at-home/server/"
chapter_id = ""
link = ""

@sleep_and_retry
@limits(calls=5, period=1)
def make_request(url, headers, params):
    response = requests.get(url, headers=headers, params=params)
    return response

def remove_invalid(name):
    invalid_chars = r'[\\/:*?"<>|]'
    valid = re.sub(invalid_chars, '', name)
    return valid

def ChangeDirec():
    global path
    path = str(askdirectory(title='Select Folder') + "/")
    if path == "/":
        path = f"{os.environ['UserProfile']}/Downloads/" if os.name == 'nt' else "/tmp/"
    app.title(path)

def get_start_end():
    try:
        start_chapter = int(entry_start.get())
    except:
        start_chapter = None

    try:
        end_chapter = int(entry_end.get())
    except:
        end_chapter = None

    return start_chapter, end_chapter

def get_chap_id():
    global chapter_id, mangadex_api, link

    link = entry.get()
    chapter_id = link
    UrlToImg()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def batchUrlToImg():
    global chapter_id, mangadex_api

    start_chapter, end_chapter = get_start_end()

    link = entry.get()
    manga_id = link
    chapter_list = get_chapter_list(manga_id, start_chapter, end_chapter)

    volumes = {}
    for chapter in chapter_list:
        volume = chapter['volume']
        if volume not in volumes:
            volumes[volume] = []
        volumes[volume].append(chapter)

    volume_manga_title = ""
    author = ""
    for volume, chapters in volumes.items():
        image_folders = []
        for i, chapter in enumerate(chapters):
            clear_screen()
            print(f"Processing Volume {volume}, Chapter {i + 1} / {len(chapters)}")
            chapter_id = chapter['id']
            # We pass the image_folders list to UrlToImg, which will append the path of the downloaded images' folder.
            manga_title, image_folder, chapter_author = UrlToImg(image_folders)
            if manga_title and not volume_manga_title:
                volume_manga_title = manga_title
            if chapter_author and not author:
                author = chapter_author

        if file_CBZ.get() == 1 and image_folders:
            output_folder = os.path.join(path, str(volume_manga_title), "CBZ")
            os.makedirs(output_folder, exist_ok=True)

            volume_str = str(volume).zfill(2)

            output_cbz_path = os.path.join(output_folder, f"{volume_manga_title} Vol. {volume_str}.cbz")
            comic_info_path = create_comic_info(output_folder, volume_manga_title, author, volume)
            convert_images_to_cbz(image_folders, output_cbz_path, comic_info_path)
            os.remove(comic_info_path)
            if file_MOBI.get() == 1:
                convert_cbz_to_mobi(output_cbz_path)

    messagebox.showinfo("Finished!", "All chapters have been processed.")

def download_image(url, image_path):
    headers = {
    }
    params = {
    }
    response = make_request(url, headers=headers, params=params)
    with open(image_path, 'wb') as f:
        f.write(response.content)

def UrlToImg(image_folders=None):
    global chapter_id, mangadex_api
    try:
        manga_title, chapter_title, chapter_num, author = get_manga_title_from_chapter(chapter_id)
        print(manga_title)
        if chapter_title: print(chapter_title)
        mangadex_api = r"https://api.mangadex.org/at-home/server/" + chapter_id
        r = urlopen(mangadex_api)
        data_json = json.loads(r.read())
        result = data_json.get('result')
        baseUrl = data_json.get('baseUrl')
        chapter_hash = data_json.get('chapter', {}).get('hash')
        chapter_data = data_json.get('chapter', {}).get('data', [])
        chapter_dataSaver = data_json.get('chapter', {}).get('dataSaver', [])

        if chapter_title:
            chapter_title = re.sub(r'\.', '', chapter_title)
            image_folder = os.path.join(path, str(manga_title), "Images", "Chapter " + str(chapter_num) + " - " + str(chapter_title))
        else:
            image_folder = os.path.join(path, str(manga_title), "Images", "Chapter " + str(chapter_num))
        os.makedirs(image_folder, exist_ok=True)
        if image_folders is not None:
            image_folders.append(image_folder)

        with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            download_tasks = []

            print("Loading images...")
            app.title("Loading images...")
            for i, image_name in enumerate(chapter_data):
                linkimg = str(baseUrl) + "/data/" + str(chapter_hash) + "/" + str(image_name)

                chapter_str = str(chapter_num).zfill(3)
                page_str = str(i + 1).zfill(2)

                output_name = f"Ch{chapter_str}_Page{page_str}.png"
                image_path = os.path.join(image_folder, output_name)

                # Download the image
                download_task = executor.submit(download_image, linkimg, image_path)
                download_tasks.append(download_task)

            # Wait for all download tasks to complete
            print("Downloading images...\n")
            app.title("Downloading images...")
            for i, download_task in enumerate(download_tasks):
                download_task.result()
                print ("\033[A                             \033[A")
                print (i+1, " / ", len(download_tasks))

            if file_PDF_fast.get() == 1:
                output_folder = os.path.join(path, str(manga_title), "PDF (Fast)")
                os.makedirs(output_folder, exist_ok=True)

                if chapter_title:
                    output_pdf_path = os.path.join(output_folder, f"Chapter {chapter_num} - {chapter_title}.pdf")
                else:
                    output_pdf_path = os.path.join(output_folder, f"Chapter {chapter_num}.pdf")

                convert_images_to_pdf_fast(image_folder, output_pdf_path, chapter_title, chapter_num)

            if file_PDF_slow.get() == 1:
                output_folder = os.path.join(path, str(manga_title), "PDF (Slow)")
                os.makedirs(output_folder, exist_ok=True)

                if chapter_title:
                    output_pdf_path = os.path.join(output_folder, f"Chapter {chapter_num} - {chapter_title}.pdf")
                else:
                    output_pdf_path = os.path.join(output_folder, f"Chapter {chapter_num}.pdf")

                convert_images_to_pdf_slow(image_folder, output_pdf_path, chapter_title, chapter_num)

            if file_CBZ.get() == 1 and image_folders is None:
                output_folder = os.path.join(path, str(manga_title), "CBZ")
                os.makedirs(output_folder, exist_ok=True)

                output_cbz_path = os.path.join(output_folder, f"{manga_title} - Chapter {chapter_num}.cbz")
                comic_info_path = create_comic_info(output_folder, manga_title, author, None)
                convert_images_to_cbz([image_folder], output_cbz_path, comic_info_path)
                os.remove(comic_info_path)
                if file_MOBI.get() == 1:
                    convert_cbz_to_mobi(output_cbz_path)


        print("Finished!")
        app.title("Finished!")
        return manga_title, image_folder, author

    except Exception as e:
        print(f"Error:", e)
        return None, None, None

def get_manga_title_from_chapter(chapter_id):
    chapter_url = f"https://api.mangadex.org/chapter/{chapter_id}"
    headers = {
        "Accept": "application/vnd.api+json",
    }
    params = {
    }

    response  = make_request(chapter_url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        for relationship in data["data"]["relationships"]:
            if relationship["type"] == "manga":
                manga_id = relationship["id"]
                break

        manga_title, author = get_manga_title(manga_id)
        chapter_title = data["data"]["attributes"]["title"]
        chapter_num = data["data"]["attributes"]["chapter"]
        if manga_title:
            manga_title = remove_invalid(manga_title)

        if chapter_title:
            chapter_title = remove_invalid(chapter_title)

        return manga_title, chapter_title, chapter_num, author
    else:
        print(f"Error: {response.status_code}")
        return None, None, None, None

def get_manga_title(manga_id):
    manga_url = f"https://api.mangadex.org/manga/{manga_id}"
    headers = {
        "Accept": "application/vnd.api+json",
    }
    params = {
        "includes[]": "author"
    }

    response  = make_request(manga_url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        author = "Unknown"
        for relationship in data["data"]["relationships"]:
            if relationship["type"] == "author":
                author = relationship["attributes"]["name"]
                break
        try:
            title = data["data"]["attributes"]["title"]["en"]
            return title, author
        except:
            title = data["data"]["attributes"]["title"]["ja-ro"]
            return title, author
    else:
        print(f"Error: {response.status_code}")
        return None, None

def get_chapter_list(manga_id, start_chapter, end_chapter, limit=500, offset=0, translatedLanguage="en",
                     contentRating=["safe", "suggestive", "erotica", "pornographic"]):

    chapter_list = []

    url = f"https://api.mangadex.org/manga/{manga_id}/feed"
    headers = {
        "Accept": "application/vnd.api+json",
    }
    params = {
        "limit": limit,
        "offset": offset,
        "translatedLanguage[]": translatedLanguage,
        "contentRating[]": contentRating,
        "order[volume]": "asc",
        "order[chapter]": "asc"
    }

    seen_chapters = set()  # Keep track of seen chapter_num values

    while url:
        response  = make_request(url, headers=headers, params=params)
        # After the first request, we will use the 'next' URL which contains all parameters.
        # So we clear the params object to avoid sending them twice.
        params = {}

        if response.status_code == 200:
            data = response.json()

            chapters_data = data.get("data", [])
            for chapter_data in chapters_data:
                attributes = chapter_data.get("attributes", {})
                chapter_id = chapter_data.get("id")
                chapter_num = attributes.get("chapter")
                volume_num = attributes.get("volume")
                external_chapter = attributes.get("externalUrl")

                if chapter_num in seen_chapters:
                    continue

                if chapter_num is not None:
                    try:
                        num = float(chapter_num)
                        if start_chapter is not None and num < start_chapter:
                            continue
                        if end_chapter is not None and num > end_chapter:
                            continue
                    except (ValueError, TypeError):
                        pass

                if external_chapter is None:
                    chapter_list.append({"id": chapter_id, "chapter": chapter_num, "volume": volume_num})
                    if chapter_num:
                        seen_chapters.add(chapter_num)

            next_link = data.get("links", {}).get("next")
            if next_link:
                url = next_link
            else:
                url = None

        else:
            print(f"Error: {response.status_code}")
            app.title("Something went wrong...")
            break

    return chapter_list

def create_comic_info(output_folder, series, author, volume):
    comic_info = ET.Element('ComicInfo', {'xmlns:xsd': 'http://www.w3.org/2001/XMLSchema', 'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance'})

    series_element = ET.SubElement(comic_info, 'Series')
    series_element.text = series

    writer_element = ET.SubElement(comic_info, 'Writer')
    writer_element.text = author

    if volume is not None:
        volume_element = ET.SubElement(comic_info, 'Volume')
        volume_element.text = str(volume)

    tree = ET.ElementTree(comic_info)

    file_path = os.path.join(output_folder, 'ComicInfo.xml')
    tree.write(file_path, encoding='utf-8', xml_declaration=True)
    return file_path

def convert_images_to_pdf_fast(folder_path, output_path, chapter_title, chapter_num):

    print("Creating pdf (fast)...")
    app.title("Creating pdf (fast)...")

    image_files = [f for f in os.listdir(folder_path) if f.endswith(('.png', '.jpg', '.jpeg'))]

    image_files.sort(key=lambda x: int(re.findall(r'\d+', x)[0]))

    if chapter_title:
        ctitle=f"{chapter_title} - Chapter {chapter_num}"
    else:
        ctitle=f"{chapter_num}"

    images = []
    for image_file in image_files:
        image_path = os.path.join(folder_path, image_file)
        img = PIL.Image.open(image_path)

        img.thumbnail((img.width, img.height))
        images.append(img)

    images[0].save(
        output_path,
        "PDF",
        resolution =100,
        save_all=True,
        append_images=images[1:],
        compress_level=0,
        title=ctitle
    )

def convert_images_to_pdf_slow(folder_path, output_path, chapter_title, chatpter_num):

    print("Creating pdf (slow)...")
    app.title("Creating pdf (slow)...")

    image_files = [f for f in os.listdir(folder_path) if f.endswith(('.png', '.jpg', '.jpeg'))]

    image_files.sort(key=lambda x: int(re.findall(r'\d+', x)[0]))

    c = canvas.Canvas(output_path, pagesize=letter)

    for image_file in image_files:
        image_path = os.path.join(folder_path, image_file)
        img = PIL.Image.open(image_path)

        if file_PDF_slow.get() == 1:
            aspect_ratio = img.width / float(img.height)

            width = letter[0]
            height = width / aspect_ratio

            c.setPageSize((width, height))
            c.drawImage(image_path, 0, 0, width, height)
            c.showPage()

    if chapter_title:
        c.setTitle(chapter_title)
    else:
        c.setTitle(chatpter_num)
    c.save()

def convert_images_to_cbz(folder_paths, output_path, comic_info_path):
    print("Creating CBZ...")
    app.title("Creating CBZ...")

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as cbz_file:
        cbz_file.write(comic_info_path, 'ComicInfo.xml')
        for folder_path in folder_paths:
            image_files = [f for f in glob.glob(os.path.join(folder_path, '*.png'))] + \
                          [f for f in glob.glob(os.path.join(folder_path, '*.jpg'))] + \
                          [f for f in glob.glob(os.path.join(folder_path, '*.jpeg'))]
            for image_file in image_files:
                cbz_file.write(image_file, os.path.basename(image_file))
def convert_cbz_to_mobi(cbz_file):
    print("Converting to MOBI...")
    app.title("Converting to MOBI...")

    cbz_dir = os.path.dirname(cbz_file)
    mobi_filename = os.path.splitext(os.path.basename(cbz_file))[0] + ".mobi"
    output_file = os.path.join(cbz_dir, mobi_filename)

    try:
        subprocess.run([
            "kcc-c2e.exe",
            os.path.basename(cbz_file),
            "-p", "KO",
            "-f", "MOBI",
            "--forcecolor",
            "--eraserainbow",
            "-u",
            "-m",
            "--blackborders",
            "-o", output_file
        ], cwd=cbz_dir, check=True)
        print("MOBI conversion successful!")
        app.title("MOBI conversion successful!")
    except subprocess.CalledProcessError as e:
        print(f"Error during MOBI conversion: {e}")
        app.title("MOBI conversion failed!")
    except FileNotFoundError:
        print("kcc-c2e.exe not found. Please ensure it's in your system's PATH.")
        app.title("kcc-c2e.exe not found!")

def toggle_mobi_switch():
    if file_CBZ.get() == 1:
        file_MOBI.configure(state="normal")
    else:
        file_MOBI.deselect()
        file_MOBI.configure(state="disabled")

# Gui section
app = customtkinter.CTk()
app.title(path)
app.resizable(width=False, height=False)
app.geometry(f"{600}x{200}")
app.iconbitmap("Icon/nerd.ico")

app.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
app.grid_rowconfigure((0, 1, 2, 3, 4), weight=1)

file_PDF_fast = customtkinter.CTkSwitch(app, text="PDF (fast)", progress_color=("#ffed9c"))
file_PDF_fast.grid(row=0, column=0, columnspan=1, padx=(10, 0), pady=(10, 0), sticky="nw")

file_PDF_slow = customtkinter.CTkSwitch(app, text="PDF (slow)", progress_color=("#ffed9c"))
file_PDF_slow.grid(row=0, column=1, columnspan=1, padx=(10, 0), pady=(10, 0), sticky="nw")

file_CBZ = customtkinter.CTkSwitch(app, text="CBZ", progress_color=("#ffed9c"), command=toggle_mobi_switch)
file_CBZ.grid(row=0, column=2, columnspan=1, padx=(10, 0), pady=(10, 0), sticky="nw")

file_MOBI = customtkinter.CTkSwitch(app, text="MOBI", progress_color=("#ffed9c"))
file_MOBI.grid(row=1, column=2, columnspan=1, padx=(10, 0), pady=(10, 0), sticky="nw")
file_MOBI.configure(state="disabled")

entry = customtkinter.CTkEntry(app, placeholder_text="Enter manga/chapter id...")
entry.grid(row=3, column=0, columnspan=3, padx=(10, 0), pady=(0, 0), sticky="swe")

entry_start = customtkinter.CTkEntry(app, placeholder_text="Start Chapter")
entry_start.grid(row=2, column=0, columnspan=1, padx=(10, 0), pady=(0, 20), sticky="sw")

entry_end = customtkinter.CTkEntry(app, placeholder_text="End Chapter")
entry_end.grid(row=2, column=1, columnspan=1, padx=(10, 0), pady=(0, 20), sticky="sw")

main_button_1 = customtkinter.CTkButton(master=app, text="Change Directory", fg_color="transparent", hover_color=("#242323"), border_width=2, command=ChangeDirec)
main_button_1.grid(row=0, column=3, padx=(20, 10), pady=(10, 20), sticky="n")

main_button_2 = customtkinter.CTkButton(master=app, fg_color="transparent", text="Go!", hover_color=("#242323"), border_width=2, command=get_chap_id)
main_button_2.grid(row=3, column=3, padx=(20, 10), pady=(0, 0), sticky="se")

main_button_3 = customtkinter.CTkButton(master=app, fg_color="transparent", text="Batch", hover_color=("#242323"), border_width=2, command=batchUrlToImg)
main_button_3.grid(row=2, column=3, padx=(20, 10), pady=(0, 20), sticky="se")

# RUN APP
app.mainloop()