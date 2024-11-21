import pyrebase
from datetime import datetime
import csv
import os
from config_firebase import firebaseConfig
import json
import shutil

def read_csv_file(file_path):
    if os.path.isfile(file_path):
        with open(file_path, mode="r", newline='') as file:
            file_data = csv.reader(file)
            file_data = list(file_data)
            return file_data
    else:
        return None
    
def update_database(data, database):
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        database.child(date).set(data)
        #print("Successfully uploaded: ", data)
    except:
        raise Exception("Could not update database")
    return None

#upload image and returns image url
def upload_image(image_path, storage, stream_name):
    image_name = os.path.basename(image_path)
    if os.path.isfile(image_path):
        cloud_path = f"{stream_name}/{image_name}"
        storage.child(cloud_path).put(image_path)
        url = storage.child(cloud_path).get_url(None)
        print(image_name, " Successfully uploaded")
        return url
    else:
        print(image_path," Not found")
        return None


def write_csv(file_name, data):
    file_name = os.path.join("./uploaded", file_name)
    with open(file_name, "a") as convert_file: 
        convert_file.write(json.dumps(data))



def compile_n_upload_iter_Cam(stream_name, storage_instance_firebase, database_instance_firebase, cloud):
    folder_path_temp = "./temp"
    if os.path.isdir(folder_path_temp):
        folder_names = []
        # GET LIST OF Valid folder names
        for folder_name in sorted(os.listdir(folder_path_temp)):
            if folder_name.startswith(stream_name) and folder_name.endswith("pr"):
                folder_names.append(folder_name)
        
        for current_folder in folder_names:
            temp_file_path = os.path.join(folder_path_temp, current_folder, "temp.csv")
            lp_file_path = os.path.join(folder_path_temp, current_folder, "lp.csv")
            temp_data = read_csv_file(temp_file_path)
            lp_data = read_csv_file(lp_file_path)
            temp_data_dict = {}
            if lp_data==None or temp_data==None:
                continue
            else:
                #convert tempdata to dict with keys as uid
                for row in temp_data:
                    temp_data_dict[row[0]] = row[1:]

                #upload image and compile data per file i.e per folder
                for lp_no in lp_data:
                    if lp_no[1] in temp_data_dict.keys():
                        data = temp_data_dict[lp_no[1]]
                        data.append(lp_no[0])
                        image_path = os.path.join("./cache", current_folder[:-2], f"{lp_no[1]}.jpg")
                        if cloud:
                            url = upload_image(image_path, storage_instance_firebase, stream_name)
                            data.append(url)
                            temp_data_dict[lp_no[1]] = data
                        else:
                            data.append(image_path)
                        write_csv(current_folder, data)    
                        
                if cloud:
                    update_database(temp_data_dict, database_instance_firebase)
                try:
                    shutil.rmtree(os.path.join(folder_path_temp, current_folder))
                    if cloud:
                        shutil.rmtree(os.path.join("./cache",current_folder[:-2]))
                except OSError as e:
                    print(f"Error: {current_folder}---{e.strerror}")

            
    else:
        raise Exception("Temp folder not found.")
    
    
#compile_n_upload_iter_Cam("CAM1", storage, database)

def compile_n_upload_iter_streams(stream_names: list, global_events: list):
    try:
        firebase = pyrebase.initialize_app(firebaseConfig)
        database = firebase.database()
        storage = firebase.storage()
    except:
        print("Could not initialize firebase")
    cloud = bool(False)
    if global_events[6].is_set():
        cloud = bool(True)

    for stream_name in stream_names:
        compile_n_upload_iter_Cam(stream_name, storage, database, cloud)
    compile_n_upload = global_events[5]
    compile_n_upload.clear()
    



