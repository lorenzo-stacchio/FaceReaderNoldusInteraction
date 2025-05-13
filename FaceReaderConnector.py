import socket
import struct
import xml.etree.ElementTree as ET
import time
import csv, json
from datetime import datetime
import pandas as pd
import requests
import os

class FaceReaderConnector:
    def __init__(self, host=None, port=None, server_url=None, log_dir='logs'):
        self.host = host
        self.port = port
        self.server_url = server_url
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.sock = None

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

    def log_classification_to_csv(self, root, csv_path):
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
                    writer.writerow([frame, ticks, label, typ, value])
                elif typ == "State":
                    state = val.find("State/string")
                    state = state.text if state is not None else ""
                    writer.writerow([frame, ticks, label, typ, state])

    def receive_and_log(self, csv_path):
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
                    self.log_classification_to_csv(root, csv_path)
                    break
            except Exception as e:
                print("XML parsing error:", e)
                continue

    def push_to_server(self, csv_path):
        column_names = ['Frame', 'Timestamp', 'Feature', 'Attribute', 'Value']
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

        # Prepare data to send
        emotion_data = {
            'emotion': dominant_emotion,
            'intensity': dominant_value,
            'valence': valence,
            'arousal': arousal
        }


    def set_log_dir(self, user_name):
        self.log_dir = f"logs/{user_name}"
        os.makedirs(self.log_dir, exist_ok = True)
        response = requests.post(self.server_url  + "/set_current_user", json={"user_name":user_name})
        print(response)
            

    def run_analysis_session(self):
        """
        Manages the analysis session: connects to FaceReader, starts analysis,
        receives logs, pushes data to the server, and stops analysis.
        """
        try:
            self.connect()
            self.send_action_message("FaceReader_Start_Analyzing")
            self.read_response()  # Optional: read initial response

            while True:
                time.sleep(1)
                timestamp = datetime.now().timestamp()
                csv_path = os.path.join(self.log_dir, f"data_{timestamp}.csv")

                self.send_action_message("FaceReader_Start_DetailedLogSending")
                self.receive_and_log(csv_path)
                self.push_to_server(csv_path)
                self.send_action_message("FaceReader_Stop_DetailedLogSending")
        except KeyboardInterrupt:
            print("Analysis session interrupted by user.")
            self.send_action_message("FaceReader_Stop_Analyzing")
        finally:
            self.disconnect()



if __name__ == '__main__':
    config_data = json.load(open("config.json"))
    
    connector = FaceReaderConnector(
        host=config_data["HOST"],
        port=config_data["PORT"],
        server_url = config_data["SERVER_URL"],
        log_dir='logs'
    )