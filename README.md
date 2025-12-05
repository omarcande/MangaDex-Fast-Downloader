# MangaDex-Fast-Downloader

A simple GUI application to download manga from MangaDex and books from your Komga server. It can download single chapters, entire manga series, or a selected range of chapters, and convert them to PDF, CBZ, and MOBI formats.

## Features

*   **MangaDex Integration**:
    *   Download entire manga series, a range of chapters, or a single chapter.
    *   Real-time search for manga titles.
    *   Convert downloads to PDF (fast and slow options), CBZ, and MOBI.
    *   Customize download location.
*   **Komga Integration**:
    *   Connect to your personal Komga server.
    *   Search for books on your server.
    *   Download books in CBZ format and automatically convert them to MOBI.
*   **User-Friendly Interface**:
    *   Tabbed interface to switch between MangaDex and Komga.
    *   Progress dialogs to show download and conversion progress.
    *   Ability to cancel long-running operations.

## How to Use

### MangaDex Tab

1.  **Search for a Manga**:
    *   Start typing a manga title in the search bar. A list of matching manga will appear below.
    *   Click on a manga from the list to select it. The manga's ID will be automatically populated.
2.  **Batch Download**:
    *   To download the entire manga, leave the "Start Chapter" and "End Chapter" fields blank and click the **Batch** button.
    *   To download a range of chapters, enter the starting and ending chapter numbers in the respective fields before clicking **Batch**.
3.  **Single Chapter Download**:
    *   Enter the chapter ID in the "Enter Chapter ID..." field.
    *   Click the **Download Chapter** button.
4.  **Output Formats**:
    *   Use the switches at the top to select your desired output formats (PDF, CBZ, MOBI).
    *   **Note**: MOBI conversion requires CBZ to be selected and the KCC path to be configured.
5.  **Configuration**:
    *   **Change Directory**: Click this button to change the default download location.
    *   **Select KCC Path**: Click this button to specify the folder containing the `kcc-c2e.exe` executable. This is required for MOBI conversion.

### Komga Tab

1.  **Server Configuration**:
    *   Enter your Komga server's URL (e.g., `http://localhost:8080`).
    *   Enter your Komga username and password.
2.  **Search for a Book**:
    *   Type the name of a book in the search bar. A list of matching books from your server will appear.
    *   Select a book from the list.
3.  **Download and Convert**:
    *   Click the **Download & Convert** button. The selected book will be downloaded as a CBZ file and then automatically converted to MOBI. The MOBI conversion requires the KCC path to be set in the MangaDex tab.
