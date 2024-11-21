import os
import cv2
import csv
from PIL import Image
import easyocr
import threading


def write_temp_lp(data, filename, folder_path):
    data = [data, filename[:-4]]
    file_path = os.path.join(folder_path, "lp.csv")
    with open(file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(data)
    return None


def process_images(folder_path):
    for filename in sorted(os.listdir(folder_path)):
        if filename[0].isdigit() and filename.endswith('.jpg'):
            image_path = os.path.join(folder_path, filename)
            try:
                image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                lp_crop_blur = cv2.GaussianBlur(image,(9,7),0)
                lp_crop_thresh = cv2.adaptiveThreshold(lp_crop_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
                cv2.imwrite(os.path.join(folder_path, filename), lp_crop_thresh)
            except IOError:
                print(f"Could not find{image_path}")
    return None


def remove_symbols(text):
    newtext = ""
    for letter in text:
        if letter.isalpha() and letter.isascii() or letter.isdigit() and letter.isascii():
            newtext += letter
    return newtext


def format_lp(text):
    dict_char_to_int = {'O': '0',
                        'I': '1',
                        'J': '3',
                        'A': '4',
                        'G': '6',
                        'S': '5',
                        'L': '1',
                        'Z': '2',
                        'E': '8',
                        'Q': '0',
                        'U': '0',
                        'T': '1'}

    dict_int_to_char = {'0': 'O',
                        '1': 'I',
                        '3': 'J',
                        '4': 'A',
                        '6': 'G',
                        '5': 'S',
                        '7': 'A',
                        '8': 'B',
                        '2': 'Z'}

    if len(text) > 9:
        formated_text = ""
        for c in text[:2]:
            if c.isdigit() and c in dict_int_to_char.keys():
                formated_text += dict_int_to_char[c]
            else:
                formated_text += c
            if len(formated_text)==2 and formated_text=="KS":
                formated_text="AS"
        for c in text[2:4]:
            if c.isalpha() and c in dict_char_to_int.keys():
                formated_text += dict_char_to_int[c]
            else:
                formated_text += c
        for c in text[4:6]:
            if c.isdigit() and c in dict_int_to_char.keys():
                formated_text += dict_int_to_char[c]
            else:
                formated_text += c
        for c in text[6:10]:
            if c.isalpha() and c in dict_char_to_int.keys():
                formated_text += dict_char_to_int[c]
            else:
                formated_text += c
        return formated_text
    else:
        return False
          

def  read_images_offline(folder_name, reader):
    folder_path = os.path.join("./temp", folder_name)
    process_images(folder_path)
    for filename in sorted(os.listdir(folder_path)):
        if  filename[0].isdigit() and filename.endswith('.jpg'):                     #filename.startswith('p')
            image_path = os.path.join(folder_path, filename)
            try:
                image = Image.open(image_path)
                detections = reader.readtext(image)
                for detection in detections:
                    bbox, text, score = detection
                    text = text.upper().replace(' ', '')
                    text = remove_symbols(text)
                    text = format_lp(text)
                    print(text)
                    write_temp_lp(text, filename, folder_path)
            except:
                print(f"Cannot read{image_path}")
    os.rename(folder_path, folder_path+"pr")
    return None


def read_images_iter_in_thread(stream_name):
    folder_path = "./temp"
    reader = easyocr.Reader(['en'], gpu=True)
    if os.path.isdir(folder_path):
        folder_names = []
        for folder_name in sorted(os.listdir(folder_path)):
            if folder_name.startswith(stream_name) and not folder_name.endswith("pr"):
                folder_names.append(folder_name)

        folder_names = sorted(folder_names[:-1])

        for current_folder in folder_names:
            read_images_offline(current_folder, reader)
    else:
        print("Temp folder does not exist")


def read_images_iter_stream_names(stream_names: list, global_events: list):
    for stream_name in stream_names:
        read_images_iter_in_thread(stream_name)
    process_n_read = global_events[4]
    compile_n_upload = global_events[5]
    process_n_read.clear()
    compile_n_upload.set()

#stream_names = ["CAM1","CAM2"]
#global_events = [0,0,0,0,0,0,0]
#read_images_iter_stream_names(stream_names, global_events)
#thread = threading.Thread(target=read_images_iter_stream_names, args=(stream_names, global_events))
#thread.start()
#thread.join()