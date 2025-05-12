from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from FaceReaderConnector import FaceReaderConnector
from config import *


class FaceReaderApp(App):
    
    def __init__(self, FaceReaderCon: FaceReaderConnector, **kwargs):
        super().__init__(**kwargs)
        self.FaceReaderCon = FaceReaderCon
    ### CONNECTION SUITE
    
    def connect_to_face_reader(self, instance):
        try:
            self.FaceReaderCon.connect()
            self.log_input.text = "Face Reader Connected Succesfully"
            # self.FaceReaderCon.send_action_message("FaceReader_Start_Analyzing")
        except Exception as e:
            self.log_input.text = f"Error in connection, have you started the Face Reader Software? \n Error: {e}"        

    def disconnect_from_face_reader(self, instance):
        self.FaceReaderCon.send_action_message("FaceReader_Stop_Analyzing")
        self.FaceReaderCon.disconnect()

    def send_to_server(self, instance):
        # Implement the logic to send data to the server
        pass

    def stop_send_to_server(self, instance):
        # Implement the logic to stop sending data to the server
        pass
    
    def build(self):
        main_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        grid_layout = GridLayout(cols=2, spacing=10, padding=10)

        # Row 1: Title spanning two columns
        # grid_layout.add_widget()
        # grid_layout.add_widget(Label())  # Empty widget to fill the second column
        # Row 2: Connect and Disconnect buttons
        grid_layout.add_widget(Button(text='Connect to Face Reader', on_press = self.connect_to_face_reader))
        grid_layout.add_widget(Button(text='Disconnect from Face Reader', on_press = self.disconnect_from_face_reader))

        # Row 3: Send and Stop buttons
        grid_layout.add_widget(Button(text='Send to Server'))
        grid_layout.add_widget(Button(text='Stop Sending to Server'))

        
        # Row 4: Log field spanning two columns using BoxLayout
        h_box_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)
        self.log_input = TextInput(hint_text='Logs will appear here...', multiline=True)
        h_box_layout.add_widget(self.log_input)
        
        main_layout.add_widget(Label(text='Face Reader Control Panel', font_size=20, halign='center'))
        main_layout.add_widget(grid_layout)
        main_layout.add_widget(h_box_layout)

        return main_layout

if __name__ == '__main__':
    connector = FaceReaderConnector(
        host=HOST,
        port=PORT,
        server_url = "https://7cd3-193-205-130-187.ngrok-free.app/",
        log_dir='logs'
    )
    FaceReaderApp(FaceReaderCon=connector).run()
