import socket
import struct
import xml.etree.ElementTree as ET
import time 
import csv
from datetime import datetime
import pandas as pd
import requests
from config import *


# --- UTILITIES ---
def build_packet(message_type: str, xml_string: str) -> bytes:
    """
    Construct the message bytes according to FaceReader format.
    - message_type: e.g., "FaceReaderAPI.Messages.ActionMessage"
    - xml_string: XML content as string
    """
    type_bytes = message_type.encode('utf-8')
    xml_bytes = xml_string.encode('utf-8')
    type_length = len(type_bytes)

    message_bytes = struct.pack('<I', type_length) + type_bytes + xml_bytes
    packet_length = len(message_bytes) + 4
    return struct.pack('<I', packet_length) + message_bytes


def send_action_message(sock, action_type: str, msg_id: str = "ID001", information: list[str] = None):
    """
    Send an action message (e.g., start analyzing, request stimuli)
    """
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<ActionMessage xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Id>{msg_id}</Id>
  <ActionType>{action_type}</ActionType>"""
    if information:
        xml += "\n  <Information>\n"
        for item in information:
            xml += f"    <string>{item}</string>\n"
        xml += "  </Information>\n"
    xml += "</ActionMessage>"

    packet = build_packet("FaceReaderAPI.Messages.ActionMessage", xml)
    sock.sendall(packet)
    print(f"Sent: {action_type}")

def read_response(sock):
    """
    Read and print one full XML response from the socket.
    """
    header = sock.recv(4)
    if not header:
        return None

    total_length = struct.unpack('<I', header)[0]
    message_data = sock.recv(total_length - 4)

    # Skip the typename length and typename
    type_len = struct.unpack('<I', message_data[:4])[0]
    xml_start = 4 + type_len
    xml_data = message_data[xml_start:]

    print("Received XML:")
    print(xml_data.decode('utf-8'))

    # Optional: parse with ElementTree
    try:
        root = ET.fromstring(xml_data.decode('utf-8'))
        return root
    except Exception as e:
        print("Failed to parse XML:", e)
        return None



def log_classification_to_csv(root, csv_path):
    frame = root.find("FrameNumber").text if root.find("FrameNumber") is not None else "?"
    ticks = root.find("FrameTimeTicks").text if root.find("FrameTimeTicks") is not None else "?"
    with open(csv_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for val in root.findall(".//ClassificationValue"):
            # print(val)
            label = val.find("Label").text if val.find("Label") is not None else "?"
            typ = val.find("Type").text
            print(label, typ)
            if typ == "Value":
                value = val.find("Value/float")
                value = value.text if value is not None else ""
                writer.writerow([frame, ticks, label, typ, value])
            elif typ == "State":
                state = val.find("State/string")
                state = state.text if state is not None else ""
                writer.writerow([frame, ticks, label, typ, state])


def receive_and_log(sock, csv_path):
    while True:
        header = sock.recv(4)
        if not header:
            print("Connection closed.")
            break

        total_len = struct.unpack('<I', header)[0]
        payload = b""
        while len(payload) < total_len - 4:
            packet = sock.recv(total_len - 4 - len(payload))
            if not packet:
                break
            payload += packet

        if len(payload) < 4:
            continue

        type_len = struct.unpack('<I', payload[:4])[0]
        xml_data = payload[4 + type_len:].decode('utf-8')

        try:
            root = ET.fromstring(xml_data)
            if root.tag == "Classification":
                log_classification_to_csv(root,csv_path)
                break
        except Exception as e:
            print("XML parsing error:", e)
            continue



def push_to_server(server_url,csv_path):
    column_names = ['Frame', 'Timestamp', 'Feature', 'Attribute', 'Value']
    # Read the CSV file without headers and assign column names
    try:
        df = pd.read_csv(csv_path, header=None, names=column_names)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return
    
    if len(df) == 0:
        return 
    
    emotions = ['Neutral', 'Happy', 'Sad', 'Angry', 'Surprised', 'Scared', 'Disgusted']

    # Filter rows corresponding to emotions
    emotion_df = df[
        (df['Attribute'] == 'Value') &
        (df['Feature'].isin(emotions))
    ]
    max_idx = emotion_df['Value'].astype(float).idxmax()

    # Retrieve the dominant emotion and its intensity
    dominant_emotion = emotion_df.loc[max_idx, 'Feature']
    dominant_value = float(emotion_df.loc[max_idx, 'Value'])
        
    # Extract valence value
    valence_row = df[(df['Feature'] == 'Valence') & (df['Attribute'] == 'Value')]
    valence = float(valence_row['Value'].values[0]) if not valence_row.empty else None

    # Extract arousal value
    arousal_row = df[(df['Feature'] == 'Arousal') & (df['Attribute'] == 'Value')]
    arousal = float(arousal_row['Value'].values[0]) if not arousal_row.empty else None
    
    
    ## MAKE MESSAGE
    emotion_message = dominant_emotion
    emotion_data = {
        emotion_message: valence  # Adjust the key to match your CSV column name
    }
    # Send a POST request to the server
    response = requests.post(server_url + "/submit_emotion", json=emotion_data)
    # Print the server's response
    print(f"Sent: {emotion_data}, Received: {response.status_code}, {response.text}")

server_url = "https://7cd3-193-205-130-187.ngrok-free.app/"
CSV_FILENAME = "test.csv"


# --- MAIN FLOW ---
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))

    # Example: start analysis
    send_action_message(s, "FaceReader_Start_Analyzing")

    # Optional: listen to response
    read_response(s)
    while True:
        time.sleep(1)
        
        timestamp_path = datetime.now().timestamp()
        csv_path = f"logs/data_{timestamp_path}.csv"

        # print(timestamp)
        # exit()
        # Example: start receiving logs
        send_action_message(s, "FaceReader_Start_DetailedLogSending")
        
        try:
            receive_and_log(s,csv_path)
            push_to_server(server_url,csv_path)
            send_action_message(s, "FaceReader_Stop_DetailedLogSending")
        except KeyboardInterrupt:
            print("Stopping...")
            send_action_message(s, "FaceReader_Stop_Analyzing")
