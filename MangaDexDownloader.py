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
import threading
import time

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
kcc_path = "G:/KCC"
mangadex_api = r"https://api.mangadex.org/at-home/server/"
chapter_id = ""
link = ""
search_timer = None
selected_manga_id = None


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

def SelectKCCPath():
    global kcc_path
    selected_path = askdirectory(title='Select KCC Folder')
    if selected_path:
        kcc_executable = os.path.join(selected_path, 'kcc-c2e.exe')
        if os.path.exists(kcc_executable):
            kcc_path = selected_path
            messagebox.showinfo("KCC Path", f"KCC path set to: {kcc_path}")
        else:
            messagebox.showerror("Error", "kcc-c2e.exe not found in the selected folder.")

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

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def download_chapter_by_id():
    main_button_2.configure(state="disabled")
    progress_dialog = ProgressDialog(app)

    download_thread = threading.Thread(target=download_chapter_thread, args=(progress_dialog,))
    download_thread.start()

def download_chapter_thread(progress_dialog):
    global chapter_id
    try:
        chapter_id = entry_chapter_id.get()
        if not chapter_id:
            return

        UrlToImg(progress_dialog)
        app.after(0, progress_dialog.complete)
    finally:
        app.after(0, lambda: main_button_2.configure(state="normal"))


def batchUrlToImg():
    main_button_3.configure(state="disabled")
    progress_dialog = ProgressDialog(app)

    batch_thread = threading.Thread(target=batch_process_thread, args=(progress_dialog,))
    batch_thread.start()

def batch_process_thread(progress_dialog):
    global chapter_id, mangadex_api, selected_manga_id
    try:
        app.after(0, progress_dialog.update_progress, "", "", "", "Fetching chapter list...", 0)

        start_chapter, end_chapter = get_start_end()

        if selected_manga_id:
            manga_id = selected_manga_id
        else:
            manga_id = entry.get()

        chapter_list = get_chapter_list(manga_id, start_chapter, end_chapter)

        volumes = {}
        for chapter in chapter_list:
            volume = chapter['volume']
            if volume not in volumes:
                volumes[volume] = []
            volumes[volume].append(chapter)

        volume_manga_title = ""
        author = ""
        summary, year, content_rating, tags, manga_dex_url = "", "", "", [], ""
        total_chapters = len(chapter_list)
        processed_chapters = 0
        for volume, chapters in volumes.items():
            image_folders = []
            for i, chapter in enumerate(chapters):
                if progress_dialog.cancelled:
                    app.after(0, progress_dialog.destroy)
                    return

                clear_screen()

                chapter_id = chapter['id']
                manga_title, image_folder, chapter_author, chapter_summary, chapter_year, chapter_content_rating, chapter_tags, chapter_manga_dex_url = UrlToImg(progress_dialog, image_folders, volume)
                if manga_title and not volume_manga_title:
                    volume_manga_title = manga_title
                if chapter_author and not author:
                    author = chapter_author
                if chapter_summary and not summary:
                    summary = chapter_summary
                if chapter_year and not year:
                    year = chapter_year
                if chapter_content_rating and not content_rating:
                    content_rating = chapter_content_rating
                if chapter_tags and not tags:
                    tags = chapter_tags
                if chapter_manga_dex_url and not manga_dex_url:
                    manga_dex_url = chapter_manga_dex_url

                processed_chapters += 1
                progress = processed_chapters / total_chapters
                app.after(0, progress_dialog.update_progress, volume_manga_title, volume, f"Ch. {chapter['chapter']}", f"Downloading Chapter {i + 1} / {len(chapters)}", progress)

            if file_CBZ.get() == 1 and image_folders:
                output_folder = os.path.join(path, str(volume_manga_title), "CBZ")
                os.makedirs(output_folder, exist_ok=True)

                volume_str = str(volume).zfill(2)

                output_cbz_path = os.path.join(output_folder, f"{volume_manga_title} Vol. {volume_str}.cbz")
                comic_info_path = create_comic_info(output_folder, volume_manga_title, author, volume, summary, year, content_rating, tags, manga_dex_url)

                app.after(0, progress_dialog.update_progress, volume_manga_title, volume, f"Vol. {volume}", "Creating CBZ...", progress)
                convert_images_to_cbz(image_folders, output_cbz_path, comic_info_path, progress_dialog)
                os.remove(comic_info_path)

                if file_MOBI.get() == 1:
                    app.after(0, progress_dialog.update_progress, volume_manga_title, volume, f"Vol. {volume}", "Converting to MOBI...", progress)
                    convert_cbz_to_mobi(output_cbz_path, progress_dialog)

        app.after(0, progress_dialog.complete)
    finally:
        app.after(0, lambda: main_button_3.configure(state="normal"))

def download_image(url, image_path):
    headers = {
    }
    params = {
    }
    response = make_request(url, headers=headers, params=params)
    with open(image_path, 'wb') as f:
        f.write(response.content)

def UrlToImg(progress_dialog=None, image_folders=None, volume=None):
    global chapter_id, mangadex_api
    try:
        manga_title, chapter_title, chapter_num, author, summary, year, content_rating, tags, manga_dex_url = get_manga_title_from_chapter(chapter_id)
        if progress_dialog:
            app.after(0, progress_dialog.update_progress, manga_title, volume, chapter_num, "Getting chapter info...", 0)
        else:
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

            if not progress_dialog:
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
            if not progress_dialog:
                print("Downloading images...\n")
                app.title("Downloading images...")

            for i, download_task in enumerate(download_tasks):
                if progress_dialog and progress_dialog.cancelled:
                    return None, None, None
                download_task.result()
                if progress_dialog:
                    app.after(0, progress_dialog.update_progress, manga_title, volume, chapter_num, f"Downloading page {i + 1} of {len(download_tasks)}", (i + 1) / len(download_tasks))
                else:
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
                comic_info_path = create_comic_info(output_folder, manga_title, author, None, summary, year, content_rating, tags, manga_dex_url)
                convert_images_to_cbz([image_folder], output_cbz_path, comic_info_path)
                os.remove(comic_info_path)
                if file_MOBI.get() == 1:
                    convert_cbz_to_mobi(output_cbz_path, progress_dialog)


        if not progress_dialog:
            print("Finished!")
            app.title("Finished!")
        return manga_title, image_folder, author, summary, year, content_rating, tags, manga_dex_url

    except Exception as e:
        print(f"Error:", e)
        return (None,) * 8

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
        manga_id = None
        for relationship in data["data"]["relationships"]:
            if relationship["type"] == "manga":
                manga_id = relationship["id"]
                break

        if manga_id:
            manga_title, author, summary, year, content_rating, tags, manga_dex_url = get_manga_title(manga_id)
        else:
            manga_title, author, summary, year, content_rating, tags, manga_dex_url = (None,) * 7

        chapter_title = data["data"]["attributes"]["title"]
        chapter_num = data["data"]["attributes"]["chapter"]
        if manga_title:
            manga_title = remove_invalid(manga_title)

        if chapter_title:
            chapter_title = remove_invalid(chapter_title)

        return manga_title, chapter_title, chapter_num, author, summary, year, content_rating, tags, manga_dex_url
    else:
        print(f"Error: {response.status_code}")
        return (None,) * 9

def get_manga_title(manga_id):
    manga_url = f"https://api.mangadex.org/manga/{manga_id}"
    headers = {
        "Accept": "application/vnd.api+json",
    }
    params = {
        "includes[]": "author"
    }

    response = make_request(manga_url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        attributes = data["data"]["attributes"]

        author = "Unknown"
        for relationship in data["data"]["relationships"]:
            if relationship["type"] == "author":
                author = relationship["attributes"]["name"]
                break

        title = attributes["title"].get("en") or attributes["title"].get("ja-ro")

        summary = attributes["description"].get("en", "")

        year = attributes.get("year")

        content_rating = attributes.get("contentRating")

        tags = [tag["attributes"]["name"]["en"] for tag in attributes["tags"]]

        manga_dex_url = f"https://mangadex.org/title/{manga_id}"

        return title, author, summary, year, content_rating, tags, manga_dex_url
    else:
        print(f"Error: {response.status_code}")
        return None, None, None, None, None, None, None

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
        response = make_request(url, headers=headers, params=params)
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

                # Normalize chapter number: treat None or empty string as "0"
                if chapter_num is None or (isinstance(chapter_num, str) and chapter_num.strip() == ""):
                    chapter_num = "0"

                # Skip if already seen (deduplication)
                if chapter_num in seen_chapters:
                    continue

                # Apply range filtering only if chapter_num is numeric
                skip = False
                if chapter_num is not None:
                    try:
                        num = float(chapter_num)
                        if start_chapter is not None and num < start_chapter:
                            skip = True
                        if end_chapter is not None and num > end_chapter:
                            skip = True
                    except (ValueError, TypeError):
                        # Non-numeric chapters (e.g. "Prologue", "Extra") are included unless filtered elsewhere
                        pass

                if skip:
                    continue

                # Only include internal chapters (no external URL)
                if external_chapter is None:
                    chapter_list.append({
                        "id": chapter_id,
                        "chapter": chapter_num,
                        "volume": volume_num
                    })
                    seen_chapters.add(chapter_num)

            # Pagination: follow the 'next' link
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

def create_comic_info(output_folder, series, author, volume, summary, year, content_rating, tags, manga_dex_url):
    comic_info = ET.Element('ComicInfo', {'xmlns:xsd': 'http://www.w3.org/2001/XMLSchema', 'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance'})

    series_element = ET.SubElement(comic_info, 'Series')
    series_element.text = series

    writer_element = ET.SubElement(comic_info, 'Writer')
    writer_element.text = author

    if volume is not None:
        volume_element = ET.SubElement(comic_info, 'Volume')
        volume_element.text = str(volume)

    if summary:
        summary_element = ET.SubElement(comic_info, 'Summary')
        summary_element.text = summary

    if year:
        year_element = ET.SubElement(comic_info, 'Year')
        year_element.text = str(year)

    if content_rating:
        rating_element = ET.SubElement(comic_info, 'AgeRating')
        rating_element.text = content_rating.capitalize()

    if tags:
        tags_element = ET.SubElement(comic_info, 'Genre')
        tags_element.text = ", ".join(tags)

    if manga_dex_url:
        web_element = ET.SubElement(comic_info, 'Web')
        web_element.text = manga_dex_url

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

def convert_images_to_cbz(folder_paths, output_path, comic_info_path, progress_dialog=None):
    if not progress_dialog:
        print("Creating CBZ...")
        app.title("Creating CBZ...")

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as cbz_file:
        cbz_file.write(comic_info_path, 'ComicInfo.xml')
        total_images = 0
        for folder_path in folder_paths:
            total_images += len([f for f in glob.glob(os.path.join(folder_path, '*.png'))]) + \
                           len([f for f in glob.glob(os.path.join(folder_path, '*.jpg'))]) + \
                           len([f for f in glob.glob(os.path.join(folder_path, '*.jpeg'))])

        images_processed = 0
        for folder_path in folder_paths:
            image_files = [f for f in glob.glob(os.path.join(folder_path, '*.png'))] + \
                          [f for f in glob.glob(os.path.join(folder_path, '*.jpg'))] + \
                          [f for f in glob.glob(os.path.join(folder_path, '*.jpeg'))]
            for image_file in image_files:
                cbz_file.write(image_file, os.path.basename(image_file))
                images_processed += 1
                if progress_dialog:
                    app.after(0, progress_dialog.update_progress, os.path.basename(output_path), "", "", f"Creating CBZ: {images_processed}/{total_images}", images_processed / total_images)

def convert_cbz_to_mobi(cbz_file, progress_dialog=None):
    if not progress_dialog:
        print("Converting to MOBI...")
        app.title("Converting to MOBI...")

    if not kcc_path:
        messagebox.showerror("Error", "KCC path not set. Please select the KCC folder first.")
        return

    try:
        temp_cbz_path = os.path.join(kcc_path, "temp.cbz")
        import shutil
        shutil.copy(cbz_file, temp_cbz_path)

        output_mobi_path = os.path.join(kcc_path, "temp.mobi")

        if progress_dialog:
            app.after(0, progress_dialog.update_progress, os.path.basename(cbz_file), "", "", "Converting to MOBI...", 0.5)

        subprocess.run([
            os.path.join(kcc_path, "kcc-c2e.exe"),
            temp_cbz_path,
            "-p", "KO",
            "-f", "MOBI",
            "--forcecolor",
            "--eraserainbow",
            "-u",
            "-m",
            "--blackborders",
            "-o", kcc_path
        ], cwd=kcc_path, check=True)

        final_mobi_filename = os.path.splitext(os.path.basename(cbz_file))[0] + ".mobi"
        final_mobi_path = os.path.join(os.path.dirname(cbz_file), final_mobi_filename)
        shutil.move(output_mobi_path, final_mobi_path)

        os.remove(temp_cbz_path)

        if progress_dialog:
            progress_dialog.update_progress(os.path.basename(cbz_file), "", "", "MOBI conversion successful!", 1)
        else:
            print("MOBI conversion successful!")
            app.title("MOBI conversion successful!")

    except subprocess.CalledProcessError as e:
        print(f"Error during MOBI conversion: {e}")
        app.title("MOBI conversion failed!")
    except FileNotFoundError:
        print("kcc-c2e.exe not found in the specified KCC path.")
        app.title("kcc-c2e.exe not found!")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        app.title("An unexpected error occurred!")

def toggle_mobi_switch():
    if file_CBZ.get() == 1:
        file_MOBI.configure(state="normal")
    else:
        file_MOBI.deselect()
        file_MOBI.configure(state="disabled")

def schedule_search(event):
    global search_timer
    if search_timer:
        app.after_cancel(search_timer)
    search_timer = app.after(300, perform_search)

def perform_search():
    query = entry.get()
    if len(query) < 3:
        listbox.grid_remove()
        return

    listbox.grid()
    listbox.delete(0, END)
    listbox.insert(END, "Searching...")

    thread = threading.Thread(target=search_manga, args=(query,))
    thread.start()

def search_manga(query):
    url = "https://api.mangadex.org/manga"
    params = {
        "title": query,
        "limit": 10,
        "contentRating[]": ["safe", "suggestive", "erotica", "pornographic"],
        "order[relevance]": "desc"
    }
    headers = {
        "Accept": "application/vnd.api+json",
    }
    response = make_request(url, headers=headers, params=params)
    if response.status_code == 200:
        results = response.json()["data"]
        app.after(0, update_listbox, results)
    else:
        app.after(0, update_listbox, [])

def update_listbox(results):
    listbox.delete(0, END)
    global manga_results
    manga_results = results

    if not results:
        listbox.insert(END, "No results found.")
        return

    for i, result in enumerate(results):
        title = result["attributes"]["title"].get("en") or result["attributes"]["title"].get("ja-ro")
        lastVolume = result["attributes"]["lastVolume"] or "N/A"
        lastChapter = result["attributes"]["lastChapter"] or "N/A"
        status = result["attributes"]["status"] or "N/A"
        listbox.insert(END, f"{i+1}. {title} [V:{lastVolume} |C:{lastChapter} |S:{status}]")

def on_select(event):
    global selected_manga_id

    selection = event.widget.curselection()
    if selection:
        index = selection[0]
        selected_manga = manga_results[index]
        selected_manga_id = selected_manga["id"]

        title = selected_manga["attributes"]["title"].get("en") or selected_manga["attributes"]["title"].get("ja-ro")
        lastVolume = selected_manga["attributes"]["lastVolume"] or "N/A"
        lastChapter = selected_manga["attributes"]["lastChapter"] or "N/A"
        status = selected_manga["attributes"]["status"] or "N/A"
        entry.delete(0, END)
        entry.insert(0, f"{title} [V:{lastVolume} |C:{lastChapter} |S:{status}]")

        listbox.grid_remove()

def toggle_download_button_state(event=None):
    if entry_chapter_id.get():
        main_button_2.configure(state="normal")
    else:
        main_button_2.configure(state="disabled")

# Gui section

class ProgressDialog(customtkinter.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Batch Conversion Progress")
        self.geometry("400x230")
        self.resizable(width=False, height=False)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure((0, 1, 2, 3, 4), weight=1)

        self.manga_label = customtkinter.CTkLabel(self, text="Manga: ")
        self.manga_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.volume_label = customtkinter.CTkLabel(self, text="Volume: ")
        self.volume_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.chapter_label = customtkinter.CTkLabel(self, text="Chapter: ")
        self.chapter_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.status_label = customtkinter.CTkLabel(self, text="Status: ")
        self.status_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")

        self.progressbar = customtkinter.CTkProgressBar(self)
        self.progressbar.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        self.progressbar.set(0)

        self.button = customtkinter.CTkButton(self, text="Cancel", command=self.cancel)
        self.button.grid(row=5, column=0, padx=10, pady=10)

        self.cancelled = False

    def update_progress(self, manga, volume, chapter, status, progress):
        self.manga_label.configure(text=f"Manga: {manga}")
        self.volume_label.configure(text=f"Volume: {volume}")
        self.chapter_label.configure(text=f"Chapter: {chapter}")
        self.status_label.configure(text=f"Status: {status}")
        self.progressbar.set(progress)
        self.update()

    def complete(self):
        self.status_label.configure(text="Status: Completed!")
        self.progressbar.set(1)
        self.button.configure(text="OK", command=self.destroy)
        self.update()

    def cancel(self):
        self.cancelled = True
        self.status_label.configure(text="Status: Cancelling...")
        self.update()

app = customtkinter.CTk()
app.title(path)
app.resizable(width=False, height=False)
app.geometry(f"{600}x{450}")
app.iconbitmap("Icon/nerd.ico")

app.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
app.grid_rowconfigure((0, 1, 2, 3, 4, 5), weight=1)

file_PDF_fast = customtkinter.CTkSwitch(app, text="PDF (fast)", progress_color=("#ffed9c"))
file_PDF_fast.grid(row=0, column=0, columnspan=1, padx=(10, 0), pady=(10, 0), sticky="nw")

file_PDF_slow = customtkinter.CTkSwitch(app, text="PDF (slow)", progress_color=("#ffed9c"))
file_PDF_slow.grid(row=0, column=1, columnspan=1, padx=(10, 0), pady=(10, 0), sticky="nw")

file_CBZ = customtkinter.CTkSwitch(app, text="CBZ", progress_color=("#ffed9c"), command=toggle_mobi_switch)
file_CBZ.grid(row=0, column=2, columnspan=1, padx=(10, 0), pady=(10, 0), sticky="nw")

file_MOBI = customtkinter.CTkSwitch(app, text="MOBI", progress_color=("#ffed9c"))
file_MOBI.grid(row=1, column=2, columnspan=1, padx=(10, 0), pady=(10, 0), sticky="nw")
file_MOBI.configure(state="disabled")

entry_chapter_id = customtkinter.CTkEntry(app, placeholder_text="Enter Chapter ID...")
entry_chapter_id.grid(row=2, column=0, columnspan=3, padx=(10, 0), pady=(10, 10), sticky="swe")
entry_chapter_id.bind("<KeyRelease>", toggle_download_button_state)

main_button_2 = customtkinter.CTkButton(master=app, fg_color="transparent", text="Download Chapter", hover_color=("#242323"), border_width=2, command=download_chapter_by_id)
main_button_2.grid(row=2, column=3, padx=(20, 10), pady=(10, 10), sticky="se")
main_button_2.configure(state="disabled")

entry_start = customtkinter.CTkEntry(app, placeholder_text="Start Chapter")
entry_start.grid(row=3, column=0, columnspan=1, padx=(10, 0), pady=(0, 20), sticky="sw")

entry_end = customtkinter.CTkEntry(app, placeholder_text="End Chapter")
entry_end.grid(row=3, column=1, columnspan=1, padx=(10, 0), pady=(0, 20), sticky="sw")

main_button_3 = customtkinter.CTkButton(master=app, fg_color="transparent", text="Batch", hover_color=("#242323"), border_width=2, command=batchUrlToImg)
main_button_3.grid(row=3, column=3, padx=(20, 10), pady=(0, 20), sticky="se")

entry = customtkinter.CTkEntry(app, placeholder_text="Search manga title...")
entry.grid(row=4, column=0, columnspan=3, padx=(10, 0), pady=(0, 0), sticky="swe")
entry.bind("<KeyRelease>", schedule_search)

listbox = Listbox(app, height=8, width=50, font=("Segoe UI", 14))
listbox.grid(row=5, column=0, columnspan=3, padx=(10, 0), pady=(10, 0), sticky="swe")
listbox.grid_remove()
listbox.bind("<<ListboxSelect>>", on_select)

main_button_1 = customtkinter.CTkButton(master=app, text="Change Directory", fg_color="transparent", hover_color=("#242323"), border_width=2, command=ChangeDirec)
main_button_1.grid(row=0, column=3, padx=(20, 10), pady=(10, 20), sticky="n")

kcc_button = customtkinter.CTkButton(master=app, text="Select KCC Path", fg_color="transparent", hover_color=("#242323"), border_width=2, command=SelectKCCPath)
kcc_button.grid(row=1, column=3, padx=(20, 10), pady=(10, 20), sticky="n")

# RUN APP
app.mainloop()
