# Translation Guide

[简体中文](../zh/translateGuide.md) | **English**


This document provides guidance and instructions for translating AALC into your language.  

It is divided into three sections (click to jump):  
1. [Translating Documentation into Your Language](#document-translation)  
2. [Translating the GUI into Your Language](#gui-translation)  
3. [Adding Support for Your Preferred Game Language (Image Support)](#image-support)  

If you encounter difficulties or have suggestions during translation, feel free to seek help or provide feedback via Issues.  

---  

## Document Translation  
This part is relatively straightforward and requires basic knowledge of Git and GitHub.  

### Steps  
1. `Fork` this repository first.  
2. Translate the document content without altering the formatting.  
3. Submit your forked repository and initiate a Pull Request.  
4. Wait for the merge.  

---  
## GUI Translation  
This part requires the Qt toolkit. You need to download `Qt Linguist` from the [Qt Official Website](https://www.qt.io/download-dev). While `Qt Linguist` is optional, it helps streamline translation and compilation of translation files (.ts) for program use. A text editor is sufficient for translation itself.  

To verify translation results:  
- Use `lrelease` or Qt Linguist’s compile feature to convert your `.ts` file into a `.qm` file.  
- Rename it to `myapp_en.qm` and set AALC’s language to `English` for testing.  

### Steps  
1. `Fork` this repository.  
2. Locate `i18n\myapp_en.ts` in the repository. Rename it to `myapp_yourLanguageCode.ts` (e.g., `zh_TW`), following international naming conventions.  
3. Open the file in `Qt Linguist` and translate each entry. Since the source text is in Chinese, refer to the English translation if needed.  
4. Upload the translated `.ts` file and initiate a Pull Request.  

### Special Notes  
- Preserve text enclosed in `{}` exactly (these are variable placeholders).  
- When editing manually, **only modify text within `<translation>Translated Text</translation>` tags**.  

---  

## Image Support  
This section requires two tools: a screenshot tool and an image editor. Use tools of your preference.  

### Steps  
1. `Fork` the repository.  
2. Take in-game screenshots matching the structure of images in `assets\images\zh_cn`.  
3. Use an image editor to **paint non-target areas black (RGB: 0,0,0 / #000000)**.  
4. Save images with identical filenames.  
5. Submit the images to the repository and initiate a Pull Request.  

### Notes  
- Maintain original image dimensions where possible. Adjust if the reference image is partial.  
- **Thoroughly test your images** to ensure recognition.  
- If *(Experimental) Auto-Language* is enabled, disable it in Settings before testing.  
- **We are unable to maintain your image resources. Limbus Company may frequently update in-game UI, requiring you to update images accordingly.**