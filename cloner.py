from tkinter import simpledialog
from tkinter import filedialog
from resemble import Resemble
from environs import Env
import soundfile as sf
from tqdm import tqdm
import tkinter as tk
import numpy as np
import requests
import backoff
import ftplib
import os

API_TOKEN = "nMQLqJXL0JQJrM3pZSMozwttxxx"
FTP_HOST = 'ftp.kombea.net'
FTP_PORT = 22
FTP_USER = 'u56862657'
FTP_PASS = 'f3TlTGtUHt&s@MYDZ*'
VOICES = {
    'Master': {
        'uuid': '',
        'pcid': ''
    },
    'Beth': {
        'uuid': '25c7823f',
        'pcid': ''
    },
    'Deanna': {
        'uuid': '9611ff3e',
        'pcid': ''
    },
    'Justin': {
        'uuid': 'b2d1bb75',
        'pcid': ''
    },
    'Vivian': {
        'uuid': 'bed1044d',
        'pcid': ''
    },
    'Primrose': {
        'uuid': '7c8e47ca',
        'pcid': ''
    },
    'Melody': {
        'uuid': '15be93bd',
        'pcid': ''
    },
    'Seth': {
        'uuid': 'a52c4efc',
        'pcid': ''
    },
    'Charles': {
        'uuid': '4c6d3da5',
        'pcid': ''
    },
    'Samantha': {
        'uuid': '266bfae9',
        'pcid': ''
    },
    'Olivia': {
        'uuid': '405b58e3',
        'pcid': ''
    },
    'Sabri': {
        'uuid': '27697927',
        'pcid': ''
    },
    'Shaun': {
        'uuid': 'abf9fd4f',
        'pcid': ''
    },
    'Danielle': {
        'uuid': 'c19b815a',
        'pcid': ''
}}
voices = list(VOICES.keys())
failed_list = []


def get_ftp_credentials():
    username = simpledialog.askstring("Username", "Enter your FTP username", parent=app)
    password = simpledialog.askstring("Password", "Enter your FTP password", parent=app)
    return username, password

@backoff.on_exception(backoff.expo, ftplib.error_perm, max_tries=5)
def upload_files(upload_directory, master_names):
    session = ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS, timeout=300)
    session.set_pasv(True)
    remote_directory = "/download/"
    session.cwd(remote_directory)
    campaign = upload_directory.split("/")[-2].replace(" ", "").replace("-", "_")
    folder = upload_directory.split("/")[-1]

    if campaign not in session.nlst():
        print(f'Creating campaign directory: {campaign}')
        session.mkd(campaign)
    session.cwd(campaign)
    if folder not in session.nlst():
        print(f'Creating folder: {folder}')
        session.mkd(folder)
    session.cwd(folder)
    folder = f'{campaign}/{folder}'
    print(f"Changing to remote directory: {folder}")
    
    print("Uploading files to FTP...")
    with tqdm(total=len(master_names)) as pbar:
        for file in master_names:
            file_path = os.path.join(upload_directory, file)
            pbar.update(1)
            with open(file_path, 'rb') as local_file:
                session.storbinary('STOR ' + file.replace("%", "[perc]").replace("#", "[hash]").replace(' ', '[space]'), local_file)
    return folder

def make_resemble_proj(name):
    print("Creating Resemble project...")
    description = "Cloninator"
    is_public = False
    is_archived = False
    is_collaborative = False
    Resemble.api_key(API_TOKEN)
    response = Resemble.v2.projects.create(name, description, is_public, is_collaborative, is_archived)
    project_uuid = response['item']['uuid']
    return project_uuid

def get_master_names(file_path, master_num, is_list_audio=False):
    data = []
    audio_names = os.listdir(file_path)
    for audio_name in audio_names:
        if is_list_audio:
            if audio_name.endswith(".wav") and f'_{master_num}_' in audio_name:
                data.append(audio_name)
        else:
            if audio_name.endswith(".wav") and audio_name.split("_")[0] == master_num:
                data.append(audio_name)    
    return data

def make_audio_request(master_names, ftp_name, resemble_id, is_list_audio, names=[], master_voice_pcid=""):
    print(f'Cloning audio files from {ftp_name} voices...')
    url = f"https://app.resemble.ai/api/v2/projects/{resemble_id}/clips"

    headers = {
        "Authorization": f'Bearer {API_TOKEN}',
        "Content-Type": "application/json",
    }
    print("Making audio files...")
    with tqdm(total=len(names) * len(master_names)) as pbar:
        for name in names:
            for master_name in master_names:
                master_name = master_name.strip().replace("%", "[perc]").replace("#", "[hash]").replace(' ', '[space]')
                if is_list_audio:
                    title = master_name.replace(f'_{master_voice_pcid}_', f'_{VOICES[name]["pcid"]}_').replace(".wav", "").replace("[perc]", "%").replace("[hash]", "#").replace("[space]", " ")
                else:
                    title = master_name.replace(master_voice_pcid, VOICES[name]["pcid"], 1).replace(".wav", "").replace("[perc]", "%").replace("[hash]", "#").replace("[space]", " ")
                body = f"<speak><resemble:convert src=\"http://ftp.kombea.net/download/{ftp_name}/{master_name}\"></resemble:convert>"
                data = {
                    "title": title,
                    "body": body,
                    "voice_uuid": VOICES[name]["uuid"],
                    "sample_rate": 22050,
                    "precision": "PCM_16",
                    "output_format": "wav",
                }
                response = send_audio_request(url, data, headers)
                
                if response.status_code == 200:
                    pbar.update(1)
                else:
                    pbar.update(1)
                    print(f"Request for {title} failed with status code {response.status_code}.")
                    failed_list.append(f"Request for {title} failed with status code {response.status_code}.")

@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=8, jitter=backoff.full_jitter)
def send_audio_request(url, json, headers):
    return requests.post(url, json=json, headers=headers, timeout=300)


def get_pods(resemble_id, page=1):
    url = "http://app.resemble.ai/api/v1/projects/" + resemble_id + "/clips?page=" + str(page) 
    headers = {
      'Authorization': "Token token=" + API_TOKEN,
      'Content-Type': "application/json",
    }
    response = requests.request("GET", url, headers=headers)
    return response.json()

def download_audio(resemble_id, file_path):
    # Get the path to the user's "Downloads" folder
    download_directory = file_path
    downloaded_files = []
    page = 1
    while True:
        project_pods_json = get_pods(resemble_id, page)
        num_res = len(project_pods_json.get('pods'))
        print("page: " + str(page) + " found pods: " + str(num_res))
        print("Downloading audio files...")
        with tqdm(total=num_res) as pbar:
            for pod in project_pods_json.get("pods"):
                title = pod.get("title")
                title = title.replace("/", "-")
                file_path = os.path.join(download_directory, title + '.wav')
                downloaded_files.append(title)
                
                if os.path.isfile(file_path):
                    print(f"File {file_path} already exists")
                else:
                    url = "http://app.resemble.ai/api/v1/projects/" + resemble_id + "/clips/" + pod.get("uuid")
                    querystring = {
                        "raw": "true"
                    }
                    headers = {
                        'Authorization': "Token token=" + API_TOKEN,
                        'Content-Type': "application/json"
                    }
                    
                    response = requests.request("GET", url, headers=headers, params=querystring, timeout=300)
                    
                    if response.status_code == 200:
                        pbar.update(1)
                        with open(file_path, 'wb') as audio_file:
                            audio_file.write(response.content)
                    else:
                        print(f"Failed to download {title} with status code {response.status_code}")
                        pbar.update(1)
                        failed_list.append(f"Failed to download {title} with status code {response.status_code}")
        
        if project_pods_json.get("current_page") == project_pods_json.get("page_count"):
            break
        if len(project_pods_json.get("pods")) == 0:
            break
        
        page += 1
    return downloaded_files

def normalize_audio(source, target):
    try:
        source_audio, _ = sf.read(source)
        target_audio, target_sr = sf.read(target)
        # Calculate the scaling factor based on peak amplitude
        source_peak_amplitude = np.max(np.abs(source_audio))
        target_peak_amplitude = np.max(np.abs(target_audio))
        scaling_factor = source_peak_amplitude / target_peak_amplitude
        # Normalize the target audio by scaling
        normalized_audio = target_audio * scaling_factor
    
        # Normalize the target file path
        normalized_target = os.path.normpath(target)
        
        sf.write(normalized_target, normalized_audio, target_sr)
    except sf.SoundFileError as e:
        print(f'Error opening sound file {e}')
    except Exception as e:
        print(f'Error occured {e}')

def delete_resemble(resemble_id):
    Resemble.v2.projects.delete(resemble_id)

def browse_file_path():
    file_path = filedialog.askdirectory()
    file_path_entry.delete(0, tk.END)
    file_path_entry.insert(0, file_path)

def run_script():
    file_path = file_path_entry.get()
    campaign = file_path.split("/")[-2].replace(" ", "_")
    folder = file_path.split("/")[-1].replace(" ", "_")
    ftp_name = f'{campaign}/{folder}'

    global FTP_USER, FTP_PASS
    FTP_USER, FTP_PASS = get_ftp_credentials()
    
    # Update pcid values based on user input
    voices_to_use = []
    for voice, pcid_entry in voice_pcid_values.items():
        pcid = pcid_entry.get()
        if pcid:
            VOICES[voice]["pcid"] = pcid
            print(f"Setting pcid for {voice} to {pcid}")
            if voice != "Master":
                voices_to_use.append(voice)
        else:
            ...

    # Get the voices selected by the user
    #voices_to_use = [voice for voice, var in voice_checkbuttons.items() if var[1].get()]
    is_list_audio = vari.get()
    delete_resemble_proj = delete.get()

    if not file_path:
        result_label.config(text="Please select file to clone")
        return

    # Update pcid values based on user input
    for voice in voices_to_use:
        VOICES[voice]["pcid"] = voice_pcid_values[voice].get()
    master_voice_pcid = voice_pcid_values["Master"].get()

    master_names = get_master_names(file_path, master_voice_pcid, is_list_audio)
    ftp_name = upload_files(file_path, master_names)
    resemble_id = make_resemble_proj(f'{ftp_name}-Clone')
    make_audio_request(master_names, ftp_name, resemble_id, is_list_audio, voices_to_use, master_voice_pcid)
    downloaded_files = download_audio(resemble_id, file_path)
    num_res = len(downloaded_files)
    print("Normalizing audio files...")
    with tqdm(total=num_res) as pbar:
        if is_list_audio:
            for target_file in downloaded_files:
                for name in voices_to_use:
                    source_file = target_file.replace(f'_{VOICES[name]["pcid"]}_', f'_{master_voice_pcid}_')
                    source = file_path + "/" + source_file + ".wav"
                    target = file_path + "/" + target_file + ".wav"
                    normalize_audio(source, target)
                pbar.update(1)
        else:
            for target_file in downloaded_files:
                target_identifier = "_".join(target_file.split("_")[1:])  # Get the identifier from the target file
                source_file = next((f for f in os.listdir(file_path) if target_identifier in f), None)
                source = file_path + "/" + source_file
                target = file_path + "/" + target_file + ".wav"
                normalize_audio(source, target)
                pbar.update(1)

    if delete_resemble_proj:
        print("Deleting Resemble project...")
        delete_resemble(resemble_id)
    with open ('failed.txt', 'w') as f:
        for item in failed_list:
            f.write("%s\n" % item)
    print("Script executed successfully!")

    result_label.config(text="Script executed successfully.")

# Create the GUI application window
app = tk.Tk()
app.title("Voice Clone GUI")

file_path_label = tk.Label(app, text="File Path:")
file_path_label.pack()
file_path_entry = tk.Entry(app)
file_path_entry.pack()

browse_button = tk.Button(app, text="Browse", command=browse_file_path)
browse_button.pack()

vari = tk.BooleanVar()
list_audio_button = tk.Checkbutton(app, text="List Audio", variable=vari)
list_audio_button.pack()

pcid_label = tk.Label(app, text="Change ProtoCall ID:\n(Leave blank to not clone)")
pcid_label.pack()

voice_pcid_values = {}
voice_checkbuttons = {}

# Create a frame for the voices with a grid layout
voices_frame = tk.Frame(app)
voices_frame.pack()

# Initialize row and column counters
row = 0
column = 0

# Create an Entry widget for the "master" pcid
pcid_label = tk.Label(voices_frame, text="Master:")
pcid_label.grid(row=row, column=column, padx=5, pady=5)
pcid_entry = tk.Entry(voices_frame)
pcid_entry.grid(row=row, column=column + 1, padx=5, pady=5)
pcid_entry.insert(0, VOICES["Master"]["pcid"])  # Set the default pcid value for "master"
voice_pcid_values["Master"] = pcid_entry  # Store the "master" pcid entry widget

row += 2

for voice in voices:
    if voice != "Master":
        # Create an Entry widget for the pcid
        pcid_label = tk.Label(voices_frame, text=voice + ":")
        pcid_label.grid(row=row, column=column, padx=5, pady=5)
        pcid_entry = tk.Entry(voices_frame)
        pcid_entry.grid(row=row, column=column + 1, padx=5, pady=5)
        # Set the default pcid value for each voice
        pcid_entry.insert(0, VOICES[voice]["pcid"])
        voice_pcid_values[voice] = pcid_entry  # Store the pcid entry widget
        
        row += 1  # Move to the next row

delete = tk.BooleanVar()
delete_button = tk.Checkbutton(app, text="Delete Resemble Project?", variable=delete)
delete_button.pack()

# Create a button to run the script
run_button = tk.Button(app, text="Run Script", command=run_script)
run_button.pack()

# Create a label for displaying the result
result_label = tk.Label(app, text="")
result_label.pack()

app.mainloop()
