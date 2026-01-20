import socket
import struct
import xml.etree.ElementTree as ET
import time
import csv, json
from datetime import datetime
import pandas as pd
import requests
import os
import threading
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests

class FaceReaderConnector:
    def __init__(self, host=None, port=None, server_url=None, log_dir='logs'):
        self.host = host
        self.port = port
        self.server_url = server_url
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.sock = None
        self.log_enabled_global = False
        self.offset_send_seconds = 1

        # self.http = requests.Session()
        # self.http.trust_env = False  # avoids Windows proxy/AV issues in many cases
        # retry = Retry(
        #     total=5,
        #     connect=5,
        #     read=5,
        #     backoff_factor=0.5,
        #     status_forcelist=(429, 500, 502, 503, 504),
        #     allowed_methods=frozenset(["POST", "GET"]),
        #     raise_on_status=False,
        # )
        # adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
        # self.http.mount("https://", adapter)
        # self.http.mount("http://", adapter)
        
    # def _post(self, path: str, payload: dict) -> bool:
    #     url = self.server_url.rstrip("/") + path
    #     try:
    #         r = self.http.post(
    #             url,
    #             json=payload,
    #             timeout=(3.05, 10),              # connect, read
    #             headers={"Connection": "close"}, # reduces flaky keep-alive behavior with some middleboxes
    #         )
    #         # If you want to treat non-2xx as failure:
    #         if r.status_code >= 400:
    #             print(f"[WARN] {url} -> {r.status_code}: {r.text[:200]}")
    #             return False
    #         return True
    #     except requests.exceptions.SSLError as e:
    #         # This is your SSLEOF case: log and continue instead of killing the thread
    #         print(f"[WARN] SSL error posting to {url}: {e}")
    #         return False
    #     except requests.exceptions.RequestException as e:
    #         print(f"[WARN] Request error posting to {url}: {e}")
    #         return False
    
    def connect(self):
        """Establish a connection to the FaceReader server."""
        # try:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        print("Connected to FaceReader.")
        # except Exception as e:
        #     print("Error", e)
        #     raise Exception

    def disconnect(self):
        """Close the connection to the FaceReader server."""
        if self.sock:
            self.sock.close()
            self.sock = None
            print("Disconnected from FaceReader.")
    
    
    def build_packet(self, message_type: str, xml_string: str) -> bytes:
        """Construct the message bytes according to FaceReader format."""
        type_bytes = message_type.encode('utf-8')
        xml_bytes = xml_string.encode('utf-8')
        type_length = len(type_bytes)
        message_bytes = struct.pack('<I', type_length) + type_bytes + xml_bytes
        packet_length = len(message_bytes) + 4
        return struct.pack('<I', packet_length) + message_bytes

    def send_action_message(self, action_type: str, msg_id: str = "ID001", information: list[str] = None):
        """Send an action message (e.g., start analyzing, request stimuli)."""
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

        packet = self.build_packet("FaceReaderAPI.Messages.ActionMessage", xml)
        self.sock.sendall(packet)
        print(f"Sent: {action_type}")

    def read_response(self):
        """Read and print one full XML response from the socket."""
        header = self.sock.recv(4)
        if not header:
            return None

        total_length = struct.unpack('<I', header)[0]
        message_data = self.sock.recv(total_length - 4)

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

    def log_classification_to_csv(self, root, csv_path, timestamp_actual):
        frame = root.find("FrameNumber").text if root.find("FrameNumber") is not None else "?"
        ticks = root.find("FrameTimeTicks").text if root.find("FrameTimeTicks") is not None else "?"
        with open(csv_path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            for val in root.findall(".//ClassificationValue"):
                label = val.find("Label").text if val.find("Label") is not None else "?"
                typ = val.find("Type").text
                if typ == "Value":
                    value = val.find("Value/float")
                    value = value.text if value is not None else ""
                    writer.writerow([frame, ticks, label, typ, value, timestamp_actual])
                elif typ == "State":
                    state = val.find("State/string")
                    state = state.text if state is not None else ""
                    writer.writerow([frame, ticks, label, typ, state, timestamp_actual])

    def receive_and_log(self, csv_path, timestamp_actual):
        while True:
            header = self.sock.recv(4)
            if not header:
                print("Connection closed.")
                break

            total_len = struct.unpack('<I', header)[0]
            payload = b""
            while len(payload) < total_len - 4:
                packet = self.sock.recv(total_len - 4 - len(payload))
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
                    self.log_classification_to_csv(root, csv_path, timestamp_actual)
                    break
            except Exception as e:
                print("XML parsing error:", e)
                continue

    def push_to_server(self, csv_path, timestamp_start, timestamp_end):
        column_names = ['Frame', 'FrameTicks', 'Feature', 'Attribute', 'Value', 'Timestamp']
        try:
            df = pd.read_csv(csv_path, header=None, names=column_names)
        except Exception as e:
            print(f"Failed to read CSV: {e}")
            return

        if len(df) == 0:
            return

        emotions = ['Neutral', 'Happy', 'Sad', 'Angry', 'Surprised', 'Scared', 'Disgusted']

        # # Filter rows corresponding to emotions
        # emotion_df = df[
        #     (df['Attribute'] == 'Value') &
        #     (df['Feature'].isin(emotions))
        # ]
        
        # ## FILTER BY TIMESTAMP
        # emotion_df['Timestamp'] = emotion_df['Timestamp'].astype(float)

        # # Filter by timestamp range
        # emotion_df = emotion_df[
        #     (emotion_df['Timestamp'] >= timestamp_start) &
        #     (emotion_df['Timestamp'] <= timestamp_end)
        # ]
        
        # if len(emotion_df) == 0:
        #     print("No recent emotions, skip")
        #     return
        # print(emotion_df)
        # # exit()
        
        # max_idx = emotion_df['Value'].astype(float).idxmax()

        # # Retrieve the dominant emotion and its intensity
        # dominant_emotion = emotion_df.loc[max_idx, 'Feature']
        # dominant_value = float(emotion_df.loc[max_idx, 'Value'])

        # # Extract valence value
        # valence_row = df[(df['Feature'] == 'Valence') & (df['Attribute'] == 'Value')]
        # valence = float(valence_row['Value'].values[0]) if not valence_row.empty else None

        # # Extract arousal value
        # arousal_row = df[(df['Feature'] == 'Arousal') & (df['Attribute'] == 'Value')]
        # arousal = float(arousal_row['Value'].values[0]) if not arousal_row.empty else None

        # # Prepare data to send
        # emotion_data = {
        #     'emotion': dominant_emotion,
        #     'intensity': dominant_value,
        #     'valence': valence,
        #     'arousal': arousal,
        #     'timestamp_actual':timestamp_end,
        # }
        
         # Ensure numeric types where needed
        df = df.copy()
        df['Timestamp'] = pd.to_numeric(df['Timestamp'], errors='coerce')
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')

        # Filter by timestamp range (apply to all features so valence/arousal align per frame)
        df_win = df[(df['Timestamp'] >= timestamp_start) & (df['Timestamp'] <= timestamp_end)].copy()
        if df_win.empty:
            print("No recent data in timestamp window, skip")
            return

        # Emotion rows in window
        emotion_df = df_win[
            (df_win['Attribute'] == 'Value') &
            (df_win['Feature'].isin(emotions)) &
            (df_win['Value'].notna())
        ].copy()

        if emotion_df.empty:
            print("No recent emotions, skip")
            return

        # 1) GROUP BY FRAME -> pick max emotion per frame
        # idxmax per group gives the row index of the max Value within each Frame
        idx = emotion_df.groupby('Frame')['Value'].idxmax()
        dom_per_frame = emotion_df.loc[idx].copy()

        # Optional: process in temporal order
        dom_per_frame = dom_per_frame.sort_values(['Timestamp', 'Frame'])

        # Precompute valence/arousal lookup per frame (within the same window)
        def per_frame_lookup(feature_name: str):
            tmp = df_win[(df_win['Feature'] == feature_name) & (df_win['Attribute'] == 'Value')].copy()
            tmp = tmp.dropna(subset=['Value'])
            # If multiple per frame, keep the last by timestamp
            tmp = tmp.sort_values(['Frame', 'Timestamp']).groupby('Frame', as_index=False).tail(1)
            return dict(zip(tmp['Frame'], tmp['Value']))

        valence_map = per_frame_lookup('Valence')
        arousal_map = per_frame_lookup('Arousal')

        # 2) PUSH ONE REQUEST PER FRAME CONSIDERED
        ACC_EMOTION_DATA = []
        for _, r in dom_per_frame.iterrows():
            frame_id = r['Frame']
            dominant_emotion = r['Feature']
            dominant_value = float(r['Value'])

            valence = float(valence_map.get(frame_id)) if frame_id in valence_map else None
            arousal = float(arousal_map.get(frame_id)) if frame_id in arousal_map else None

            emotion_data = {
                'frame': int(frame_id) if pd.notna(frame_id) else frame_id,
                'emotion': dominant_emotion,
                'intensity': dominant_value,
                'valence': valence,
                'arousal': arousal,
                'timestamp_actual': float(r['Timestamp']),  # per-frame timestamp
            }
            ACC_EMOTION_DATA.append(emotion_data)

            # send it (replace with your actual request call)
            # self._post_emotion(emotion_data)
            # or requests.post(self.server_url, json=emotion_data)
            # print("PUSH:", emotion_data)
            ### SEND TO SERVER
            
            # response = requests.post(self.server_url + "/submit_emotion", json=emotion_df.to_json(orient="records"))
            # # Print the server's response
            # print(f"Sent: {emotion_df}, Received: {response.status_code}, {response.text}")
            
        response = requests.post(self.server_url + "/submit_emotion", json=ACC_EMOTION_DATA)
        # Print the server's response
        # ok = self._post("/submit_emotion", emotion_data)
        # if ok:
        #     print(f"Sent: {emotion_data}, Received: {response.status_code}, {response.text}")
        # else:
        #     print("ERROR IN SENT")
        print(f"Sent: {emotion_data}, Received: {response.status_code}, {response.text}")

    def set_log_dir(self, user_name):
        self.log_dir = f"logs/{user_name}"
        os.makedirs(self.log_dir, exist_ok = True)
        response = requests.post(self.server_url  + "/set_current_user", json={"user_name":user_name})
        return response

    def set_stimuli(self, stimuli):
        response = requests.post(self.server_url  + "/set_current_stimuli", json={"stimuli":stimuli})
        return response.json()["log"]
    
    def aggregate_emotions(self):
        response = requests.get(self.server_url  + "/aggregate_emotions")
        to_return = response.json()["log"]
        requests.post(self.server_url + "/submit_chat_log", json={"VALUE": "Emotions Aggregated for Prompt", "LOGTYPE": "EMOTIONS_AGGREGATED", "mode": "emotion conditioning"})
        return to_return

    
    def restart_server(self):
        response = requests.get(self.server_url  + "/restart_chat")
        return response.json()["url"]

    def start_session(self):
        
        """
        Manages the analysis session: connects to FaceReader, starts analysis,
        receives logs, pushes data to the server, and stops analysis.
        """
        
        try:
            self.send_action_message("FaceReader_Start_Analyzing")
            self.read_response()  # Optional: read initial response
            self.log_enabled_global = True
            timestamp_beginning = datetime.now().timestamp()
            csv_path = os.path.join(self.log_dir, f"data_{timestamp_beginning}.csv")

            time_stamp_check_offset = datetime.now().timestamp()

            while self.log_enabled_global:
                self.send_action_message("FaceReader_Start_DetailedLogSending")
                timestamp_actual = datetime.now().timestamp()
                self.receive_and_log(csv_path, timestamp_actual)
                self.send_action_message("FaceReader_Stop_DetailedLogSending")
                timestamp_loop = datetime.now().timestamp()
                if timestamp_loop > (time_stamp_check_offset + self.offset_send_seconds):
                    self.push_to_server(csv_path, time_stamp_check_offset, timestamp_loop)
                    time_stamp_check_offset = timestamp_loop
                if not self.log_enabled_global:
                    break
               
        except KeyboardInterrupt:
            print("Analysis session interrupted by user.")
            self.send_action_message("FaceReader_Stop_Analyzing")
        finally:
            self.disconnect()


    def stop_session(self):
        try:
            self.send_action_message("FaceReader_Stop_Analyzing")
            self.log_enabled_global = False
            # self.disconnect()
        except KeyboardInterrupt:
            print("Error.")
        # finally:
        #     self.disconnect()


if __name__ == '__main__':
    config_data = json.load(open("config.json"))
    
    connector = FaceReaderConnector(
        host=config_data["HOST"],
        port=config_data["PORT"],
        server_url = config_data["SERVER_URL"],
        log_dir='logs'
    )
    
    connector.connect()
    # connector.start_session()
    # connector.stop_session()
    
    # Create and start a new thread to run start_session
    session_thread = threading.Thread(target=connector.start_session)
    session_thread.start()

    # Let the session run for a certain period
    time.sleep(4)  # Adjust the sleep time as needed

    # Stop the session by modifying the global variable
    connector.stop_session()

    # Wait for the session thread to finish
    session_thread.join()